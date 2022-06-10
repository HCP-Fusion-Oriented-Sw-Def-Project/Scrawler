import os
import pickle
import time
import xml.etree.ElementTree as xeTree
import cv2
import numpy as np

from uiautomator import device
from backend.edge import Edge
from backend.screen import Screen, Stack, is_same_screen
from backend.xml_tree import parse_nodes
from backend.crawler import get_package_name
from backend.model import GUIModel
from compare.utility import get_screen_sim

from get_new_path.utility import get_screen_sim_score, get_edge_sim_score, is_same_one

"""
流程 1. 记录交互元素的坐标
    2. 在基础版本重放 获得场景模型
    3. 将新版本模型复制到与2同一个文件夹中
    4. 然后运行work代码 查看结果
"""

"""
都是坐标序列
[[x, y], [x, y], [x, y], [x, y]]

[[495,31], [[333,45]]
"""


class Searcher:
    """
    搜索类
    """

    def __init__(self, package, event_sequences, path, is_circle):
        # 包名
        self.package_name = package

        # 主要是在更新模型中进行搜索
        self.updated_model = None
        # 存储场景模型
        self.scenario_model = None

        # 测试用例走过的页面和边
        # 反正是按照顺序走过的 所以用列表即可
        self.screens = {}
        self.edges = []

        # 事件序列 记录的是元素的坐标
        self.event_sequences = event_sequences

        self.screen_id = 1

        # 当前所在页面
        self.cur_screen_id = -1

        # 当前点击元素
        self.clicked_node = None

        # 页面对比时 所用的相似参数
        self.distinct_rate = 0.9

        # 存储路径
        self.path = path

        # 页面映射
        self.screens_map = {}

        # 相似度阈值
        self.text_sim = 0.4

        # 所有的结果页面转移 包含的是页面id
        self.result_screen_transfer = []

        # 所有结果的边的转移 包含的是一条条边的序列 [[edge1,edge2], [edgexx]]
        self.result_edges_transfer = []

        # 是否有环
        self.is_circle = is_circle

        # 候选路径的最大值
        self.max_candidate_num = 50

        # # 候选路径最小长度和最大长度
        # self.min_length = len(event_sequences) + 1 - 2
        # self.max_length = len(event_sequences) + 1 + 2

    def open_app(self):
        """
        打开应用
        :param package_name:
        :return:
        """

        cmd = 'adb shell monkey -p ' + self.package_name + ' -c android.intent.category.LAUNCHER 1'
        os.system(cmd)
        time.sleep(3)

    def close_app(self):
        """
        关闭应用
        :return:
        """

        cmd = "adb shell am force-stop " + self.package_name
        os.system(cmd)

    def get_activity_name(self):
        """
        获取当前activity名字 使用adb工具
        :return:
        """

        cmd = 'adb shell \"dumpsys window w | grep name=\" '
        result = os.popen(cmd)
        res = result.buffer.read().decode(encoding='utf-8')
        activity_name = ''
        for line in res.splitlines():
            if "activity" in line.lower():
                activity_name = line.split('/')[1][:-1]
                break

        return activity_name

    def action_click(self, node):
        """
        点击事件
        :return:
        """

        x, y = node.get_click_position()
        device.click(x, y)

        print('当前点击元素')
        print(node.attrib)
        print(node.idx)

    def get_tmp_screen(self):
        """
        dump当前页面 获得一个临时的screen节点
        :return:
        """

        xml_info = device.dump(compressed=False)
        root = xeTree.fromstring(xml_info)
        nodes = parse_nodes(root)
        act_name = self.get_activity_name()
        tmp_screen = Screen(nodes, -1, act_name)

        return tmp_screen

    def has_same_screen(self, tmp_screen):
        """
        判断是否已有相同页面
        :param tmp_screen:
        :return:
        """

        for screen_id in self.screens.keys():
            screen = self.screens[screen_id]
            if is_same_screen(screen, tmp_screen, self.distinct_rate):
                return screen_id

        return -1

    def save_screen(self, screen):
        """
        保存页面信息
        :return:
        """

        sub_dir = self.path + '/' + 'scenario_screens'
        if not os.path.exists(sub_dir):
            os.makedirs(sub_dir)

        device.dump(sub_dir + '/' + str(screen.id) + '.xml', compressed=False)
        device.screenshot(sub_dir + '/' + str(screen.id) + '.png')
        screen.shot_dir = sub_dir + '/' + str(screen.id) + '.png'

    def is_valid_edge(self, stack, d_id, root_edge):
        """
        用于在寻找边转移路径的时候 避免对环进行搜索
        :return:
        """

        edge = self.updated_model.edges[d_id - 1]
        des_screen_id = edge.end_id

        all_screen_id = []
        for e_id in stack.items:
            if e_id != -1:
                tmp_edge = self.updated_model.edges[e_id - 1]
            else:
                tmp_edge = root_edge
            all_screen_id.append(tmp_edge.begin_id)
            all_screen_id.append(tmp_edge.end_id)

        if des_screen_id not in all_screen_id:
            return True

        return False

    def search_edge_transfer3(self, source_id, des_id):
        """
        不需要先找页面转移 再映射成边 可以直接去找边的转移
        :param source_id:
        :param des_id:
        :return:
        """

        root_edge = Edge(-1, source_id, -1)
        root_edge.id = -1
        root_edge.des = []
        root_edge.visited_des = []

        count = 1
        # 找出root_edge所有的后继边
        for edge in self.updated_model.edges:
            edge.id = count
            edge.des = []
            edge.visited_des = []
            count += 1
            if edge.begin_id == root_edge.end_id and edge.begin_id == source_id:
                root_edge.des.append(edge.id)

        # 为其它边构造后继边
        for edge in self.updated_model.edges:
            for tmp_edge in self.updated_model.edges:
                if edge.end_id == tmp_edge.begin_id:
                    edge.des.append(tmp_edge.id)

        stack = Stack()
        stack.push(root_edge.id)

        while not stack.empty():
            top_id = stack.top()
            if top_id == -1:
                edge = root_edge
            else:
                edge = self.updated_model.edges[top_id - 1]

            # 搜索已达最后一条边
            if edge.end_id == des_id:
                # 把栈中所有元素取出
                edge_transfer = stack.items.copy()
                if len(self.result_edges_transfer) < self.max_candidate_num:
                    # if self.min_length <= len(edge_transfer) <= self.max_length:
                    self.result_edges_transfer.append(edge_transfer)
                else:
                    break
                # 元素出栈
                stack.pop()
            else:
                if edge.des != edge.visited_des:
                    for d_id in edge.des:
                        if d_id not in edge.visited_des:
                            edge.visited_des.append(d_id)
                            # 不是这样判断的 应该是当前边的目标页面不能是之前边节点中的起始页面
                            # 避免有环 当前的实现不能避免有环
                            if self.is_circle is False:
                                if d_id not in stack.items and self.is_valid_edge(stack, d_id, root_edge):
                                    # 元素进栈
                                    stack.push(d_id)
                                    break
                            else:
                                if d_id not in stack.items:
                                    # 元素进栈
                                    stack.push(d_id)
                                    break
                else:
                    # 元素出栈
                    stack.pop()
                    # 以下访问过的边清空
                    edge.visited_des = []

        print(self.result_edges_transfer)

    def replay(self):
        """
        将事件序列进行重放 然后构造重放所发生的边的转移
        :return:
        """

        # 首先打开app
        self.open_app()

        success_flag = True

        for pos in self.event_sequences:

            if self.cur_screen_id == -1:
                # 首先dump当前的页面 然后寻找节点进行点击
                xml_info = device.dump(compressed=False)
                root = xeTree.fromstring(xml_info)
                nodes = parse_nodes(root)
                act_name = self.get_activity_name()
                screen = Screen(nodes, self.screen_id, act_name)

                # 更新screen
                self.cur_screen_id = screen.id

                # 将其加入screens中
                self.screens[self.cur_screen_id] = screen
                self.screen_id += 1
                self.save_screen(screen)

                # 然后寻找点击的 pos 所对应的元素
                for node in screen.nodes:
                    if not node.children:
                        if pos[0] == node.loc_x and \
                                pos[1] == node.loc_y and \
                                'Group' not in node.attrib['class']:
                            self.clicked_node = node
                            break

                if self.clicked_node is None:
                    print('无法找到当前点击元素')
                    print('重放初始序列失败')
                    success_flag = False
                    break

                # 然后点击元素
                self.action_click(self.clicked_node)

                time.sleep(5)

            else:
                # 判断页面是否发生转移
                tmp_screen = self.get_tmp_screen()
                exist_screen_id = self.has_same_screen(tmp_screen)
                if exist_screen_id == self.cur_screen_id:
                    print('页面不发生转移')
                    print('重放序列失败')
                    success_flag = False
                    break

                # 记录页面的转移 记录边
                tmp_screen.id = self.screen_id

                # 将页面加入
                self.screens[tmp_screen.id] = tmp_screen
                self.screen_id += 1
                self.save_screen(tmp_screen)

                edge = Edge(self.cur_screen_id, tmp_screen.id, self.clicked_node.idx)
                self.edges.append(edge)
                # 记录页面之间的转移
                self.screens[self.cur_screen_id].des.append(tmp_screen.id)
                self.cur_screen_id = tmp_screen.id

                # 然后遍历当前节点元素 进行点击
                # 然后寻找点击的 pos 所对应的元素
                self.clicked_node = None
                for node in tmp_screen.nodes:
                    if not node.children:
                        if pos[0] == node.loc_x and pos[1] == node.loc_y:
                            self.clicked_node = node
                            break

                if self.clicked_node is None:
                    print('无法找到当前点击元素')
                    print('重放初始序列失败')
                    success_flag = False
                    break

                # 然后点击元素
                self.action_click(self.clicked_node)
                time.sleep(5)

        # 在循环外还需要最后记录一次
        # 判断页面是否发生转移
        tmp_screen = self.get_tmp_screen()
        exist_screen_id = self.has_same_screen(tmp_screen)
        if exist_screen_id == self.cur_screen_id:
            print('页面不发生转移')
            print('重放序列失败')

        # 记录页面的转移 记录边
        tmp_screen.id = self.screen_id

        # 将页面加入
        self.screens[tmp_screen.id] = tmp_screen
        self.screen_id += 1
        self.save_screen(tmp_screen)

        edge = Edge(self.cur_screen_id, tmp_screen.id, self.clicked_node.idx)
        self.edges.append(edge)
        # 记录页面之间的转移
        self.screens[self.cur_screen_id].des.append(tmp_screen.id)
        self.cur_screen_id = tmp_screen.id

        print('重放成功')
        print('edge')
        for edge in self.edges:
            print('---')
            print('begin')
            print(edge.begin_id)
            print('end')
            print(edge.end_id)
            print('node')
            print(edge.node_id)
            print('---')

        print('screen')
        for key in self.screens:
            screen = self.screens[key]
            s = ''
            for node in screen.nodes:
                if node.attrib['text'] != '':
                    s += node.attrib['text']
            print(screen.id)
            print(s)
            print('-------------')

        # 保存模型
        self.scenario_model = GUIModel(self.screens, self.edges)
        model = pickle.dumps(self.scenario_model)
        with open(self.path + '/scenario_model', 'wb') as f:
            f.write(model)

    def read_model(self):
        """
        读取模型
        :return:
        """

        f = open(self.path + '/scenario_model', 'rb')
        self.scenario_model = pickle.load(f)
        f = open(self.path + '/updated_model', 'rb')
        self.updated_model = pickle.load(f)

        # 初始化页面的匹配id 以及边的id和匹配id 因为边本身没有id
        for key in self.scenario_model.screens:
            self.scenario_model.screens[key].matched_id = -1

        for key in self.updated_model.screens:
            self.updated_model.screens[key].matched_id = -1

        # 将updated模型的screen转到当前文件夹下
        updated_screen_dir = self.path + '/' + 'updated_screens'

        if not os.path.exists(updated_screen_dir):
            os.makedirs(updated_screen_dir)

        for key in self.updated_model.screens:
            screen = self.updated_model.screens[key]
            img = cv2.imread(screen.shot_dir)
            cv2.imwrite(updated_screen_dir + '/' + str(screen.id) + '.png', img)

    def map_for_screens(self):
        """
        将场景的起点和终点与updated_model中的页面进行匹配
        :return:
        """

        for x_key in self.scenario_model.screens.keys():
            s_screen = self.scenario_model.screens[x_key]

            max_score = 0
            matched_screen = None

            # 去找到与它相似度最大的页面
            for y_key in self.updated_model.screens.keys():
                tmp_screen = self.updated_model.screens[y_key]
                # if tmp_screen.matched_id == -1:
                sim_score = get_screen_sim(s_screen, tmp_screen)
                if sim_score >= self.text_sim and sim_score > max_score:
                    max_score = sim_score
                    matched_screen = tmp_screen

            if matched_screen is not None:
                s_screen.matched_id = matched_screen.id
                matched_screen.matched_id = s_screen.id

        # 再补充一下 如果没有映射到页面 但是又返回去了 那么去找到个之前同样的页面即可
        for key in self.scenario_model.screens.keys():
            screen = self.scenario_model.screens[key]
            if screen.matched_id == -1:
                for l_key in self.scenario_model.screens.keys():
                    if l_key != key:
                        l_screen = self.scenario_model.screens[l_key]
                        if is_same_one(screen, l_screen):
                            if l_screen.matched_id != -1:
                                screen.matched_id = l_screen.matched_id

        for key in self.scenario_model.screens:
            screen = self.scenario_model.screens[key]
            if screen.matched_id != -1:
                self.screens_map[screen.id] = screen.matched_id


        print(self.screens_map)


    def map_for_screens2(self):
        """
        使用邻接矩阵的匹配方法
        之前的那种元素匹配和页面匹配的写法其实都不太对 以后再改了
        :return:
        """

        m = len(self.scenario_model.screens.keys())
        n = len(self.updated_model.screens.keys())

        scores = np.zeros((m, n))

        i = 0
        for x_key in self.scenario_model.screens.keys():
            s_screen = self.scenario_model.screens[x_key]
            j = 0
            for y_key in self.updated_model.screens.keys():
                tmp_screen = self.updated_model.screens[y_key]
                sim_score = get_screen_sim(s_screen, tmp_screen)
                scores[i][j] = sim_score
                j += 1

            i += 1

        print(scores)




    def get_result_edges_sequences(self):
        """
        获取最后所有的边转移的序列
        :return:
        """

        # 首先找的场景的起点和终点
        screen_list = []
        for key in self.scenario_model.screens.keys():
            screen_list.append(key)

        begin_id = screen_list[0]
        begin_screen = self.scenario_model.screens[begin_id]
        end_id = screen_list[len(screen_list) - 1]
        end_screen = self.scenario_model.screens[end_id]

        # 去新版本上搜索路径 所有的边转移序列保存在 self.result_edge_transfer中
        self.search_edge_transfer3(begin_screen.matched_id, end_screen.matched_id)

        new_edges_transfer = []
        for edge_id_list in self.result_edges_transfer:
            if edge_id_list != [-1]:
                edge_id_list = edge_id_list[1:]
                new_edges_transfer.append(edge_id_list)

        self.result_edges_transfer = new_edges_transfer

    def save_work(self):
        """
        将所有的候选路径和最优路径找出
        :return:
        """

        result_dir = self.path + '/' + 'result'
        candidate_path = result_dir + '/' + 'candidate'
        optimal_path = result_dir + '/' + 'optimal'

        dir_list = [candidate_path, optimal_path]
        for path in dir_list:
            if not os.path.exists(path):
                os.makedirs(path)

        if len(self.result_edges_transfer) != 0:
            count = 1
            for edge_id_list in self.result_edges_transfer:
                # edge_id_list = edge_id_list[1:]
                if len(edge_id_list) != 0:
                    tmp_dir = candidate_path + '/' + str(count)
                    if not os.path.exists(tmp_dir):
                        os.makedirs(tmp_dir)
                    print('------------------')
                    e_count = 1
                    for e_id in edge_id_list:
                        # 然后先找出边 然后找到页面 然后找到节点 画图
                        edge = self.updated_model.edges[e_id - 1]
                        print(edge.begin_id)
                        # 然后找到页面
                        screen = self.updated_model.screens[edge.begin_id]
                        # 然后找到节点
                        clicked_node = screen.get_node_by_id(edge.node_id)

                        img_path = self.path + '/' + 'updated_screens' + '/' + str(screen.id) + '.png'
                        # 读取图片
                        img = cv2.imread(img_path)
                        # 画出点击节点
                        x1, y1, x2, y2 = clicked_node.parse_bounds()
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)

                        cv2.imwrite(tmp_dir + '/' + 'action' + str(e_count) + '.png', img)
                        e_count += 1

                    # 然后再搜集一下终点的页面
                    e_id = edge_id_list[len(edge_id_list) - 1]
                    edge = self.updated_model.edges[e_id - 1]
                    # 然后找到页面
                    screen = self.updated_model.screens[edge.end_id]
                    img_path = self.path + '/' + 'updated_screens' + '/' + str(screen.id) + '.png'
                    # 读取图片
                    img = cv2.imread(img_path)
                    cv2.imwrite(tmp_dir + '/' + 'destination.png', img)

                    count += 1

    def work(self):
        """
        主函数
        :return:
        """

        self.read_model()
        self.map_for_screens()
        self.get_result_edges_sequences()
        self.save_work()

        # 以上为准备工作 以下为寻路工作
        source_screens = []
        source_edges = self.scenario_model.edges
        for key in self.scenario_model.screens:
            screen = self.scenario_model.screens[key]
            source_screens.append(screen)

        max_score = 0
        similar_transfer_id = -1

        print('候选路径的数目：' + str(len(self.result_edges_transfer)))

        # 遍历所得结果的界面转移序列 找出相似度最大的那个转移序列
        for i in range(len(self.result_edges_transfer)):
            tmp_result_path = self.result_edges_transfer[i]
            screens, edges = self.get_edges_and_screens(tmp_result_path)
            score = get_edge_sequences_sim(source_screens, source_edges, screens, edges, 1, 0, 3, 3)
            if score > max_score:
                max_score = score
                similar_transfer_id = i + 1

        print('最佳路径的编号为：' + str(similar_transfer_id))

        # 然后保存这条路径
        result_dir = self.path + '/' + 'result'
        optimal_path = result_dir + '/' + 'optimal'
        tmp_dir = optimal_path + '/' + str(similar_transfer_id)
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        if similar_transfer_id == -1:
            print('无法找到路径')
        else:
            edge_id_list = self.result_edges_transfer[similar_transfer_id - 1]

            e_count = 1
            for e_id in edge_id_list:
                # 然后先找出边 然后找到页面 然后找到节点 画图
                edge = self.updated_model.edges[e_id - 1]
                # print(edge.begin_id)
                # 然后找到页面
                screen = self.updated_model.screens[edge.begin_id]
                # 然后找到节点
                clicked_node = screen.get_node_by_id(edge.node_id)

                img_path = self.path + '/' + 'updated_screens' + '/' + str(screen.id) + '.png'
                # 读取图片
                img = cv2.imread(img_path)
                # 画出点击节点
                x1, y1, x2, y2 = clicked_node.parse_bounds()
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)

                cv2.imwrite(tmp_dir + '/' + 'action' + str(e_count) + '.png', img)
                e_count += 1

            # 然后搜集一下终点的页面
            e_id = edge_id_list[len(edge_id_list) - 1]
            edge = self.updated_model.edges[e_id - 1]
            # 然后找到页面
            screen = self.updated_model.screens[edge.end_id]
            img_path = self.path + '/' + 'updated_screens' + '/' + str(screen.id) + '.png'
            # 读取图片
            img = cv2.imread(img_path)
            cv2.imwrite(tmp_dir + '/' + 'destination.png', img)


    def get_edges_and_screens(self, edge_path):
        """
        输入边序号 返回所有的边 以及screens
        :param edge_path:
        :return:
        """

        screens = []
        edges = []

        # 先搜集边
        for e_id in edge_path:
            edges.append(self.updated_model.edges[e_id - 1])
            edge = self.updated_model.edges[e_id - 1]
            screen = self.updated_model.screens[edge.begin_id]
            screens.append(screen)

        # 然后搜集页面  先搜集所有边的begin_id 然后最后搜一个end_id即可
        final_edge_id = edge_path[len(edge_path) - 1]
        final_edge = self.updated_model.edges[final_edge_id - 1]
        des_screen = self.updated_model.screens[final_edge.end_id]

        screens.append(des_screen)

        return screens, edges

    def get_elements(self):
        """
        临时获取页面数据
        :return:
        """

        xml_info = device.dump(compressed=False)
        root = xeTree.fromstring(xml_info)
        nodes = parse_nodes(root)
        # act_name = self.get_activity_name()
        # tmp_screen = Screen(nodes, -1, act_name)
        for node in nodes:
            if not node.children:
                print(node.attrib)

    def tmp(self):
        self.read_model()
        self.map_for_screens()
        self.map_for_screens2()


def get_edge_sequences_sim(source_screens, source_edges, screens, edges, s_i, t_j, w_length, step):
    """
    利用序列概率转移算法来计算
    :param source_screens:
    数组
    :param source_edges:
    数组
    :param screens:
    数组
    :param edges:
    数组
    :param s_i:
    数组中的序号 代表当前需要匹配的页面
    :param t_j:
    数组中的序号 代表上一个匹配好了的页面
    :param step:
    步长 用几步的相似度 去近似 整个序列的相似度
    :return:
    W is the maximal number of elements in F that a single element in E can be converted to
    w_length =
    """

    # 首先给出current score
    current_score = 0

    # 如果超出了 原序列的范围
    if s_i == len(source_screens):
        return current_score

    # 如果超出了设置的步长
    if step > w_length:
        return 0

    # 获取t_j之后三步可达的页面

    # 获得当前需要匹配的页面s_i
    screen_s_i = source_screens[s_i]

    # 搜集可达页面
    for i in range(1, w_length + 1):
        if t_j + i < len(screens):
            screen_t_k = screens[t_j + i]
            # 计算这些候选页面与页面s_i的相似度 要计算步长cost
            jump_t = i
            jump_s = 1
            jump_cost = np.log2(abs(jump_t - jump_s) + 1) + 1
            screen_sim = get_screen_sim_score(screen_s_i, screen_t_k, s_i, s_i + 1, t_j, t_j + i)
            edge_sim = get_edge_sim_score(source_screens, source_edges, screens, edges, screen_s_i, screen_t_k)
            # 递归的含义就是 默认这一步可达的t_j + i 与s_i是匹配的 然后去计算后面的转移概率
            score_next = get_edge_sequences_sim(source_screens, source_edges, screens, edges,
                                                s_i + 1, t_j + i, w_length, step)

            sim = screen_sim + edge_sim + score_next
            sim /= jump_cost

            if sim > current_score:
                current_score = sim

    return current_score


def main():
    package_name = get_package_name()
    event_sequences = [[241,140]]

    path = 'E:/graduation/scrob_experiment/RQ3-compare/Dianping 2'
    obj = Searcher(package_name, event_sequences, path, False)
    # obj.replay()
    # obj.work()
    # obj.get_elements()


main()
