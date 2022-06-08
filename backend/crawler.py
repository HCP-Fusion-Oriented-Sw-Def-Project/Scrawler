import logging
import os
import pickle
import time

import xml.etree.ElementTree as xeTree
from uiautomator import device

from backend.edge import Edge, has_same_edge
from backend.model import GUIModel
from backend.screen import is_same_screen, Screen, Stack
from backend.visualize import VisualTool
from backend.xml_tree import parse_nodes


class Crawler():
    """
    遍历类
    """

    def __init__(self, package, path):
        # 记录每个activity下有多少个页面
        self.act_count = {}

        # 当前页面的id
        self.cur_screen_id = -1

        # screen id
        self.screen_id = 1

        # 当前深度
        self.cur_depth = 0

        # 当前点击的节点
        self.clicked_node = None

        # 包名
        self.package_name = package

        # 路径
        self.path = path

        # 遍历过的页面 {id} = screen
        self.screens = {}

        # 所有的边
        self.edges = []

        # 开始遍历和结束遍历时间
        self.start_time = 0
        self.cost_time = 0

        # 页面id栈
        self.stack = Stack()

        # 配置文件 还可以补充信息用于自动安装app

        # max_depth 指的是到达那个层次的页面后 便不再进行遍历
        self.max_depth = 2
        self.max_time = 3600 * 6
        self.action_interval = 5
        # 重放页面所尝试的次数
        self.replay_try_times = 3

        # 判断重新打开app时能否回到初始页面
        self.reopen_to_first = True

        # 页面对比时 所用的相似参数
        self.distinct_rate = 0.9

        # 元素黑名单
        self.black_elem_list = {
            'text': ['退出', '升级', '退出',
                     '下载', '注销', '上传',
                     '同步', '安装', 'download',
                     'capture', '确定', '取消',
                     '删除', '保存', 'save',
                     'add', 'delete', '增加',
                     '删除', '同步', '排序',
                     'confirm', 'yes', 'update',
                     'upload', 'quit', 'sort', 'ok', 'upgrade', 'Rate'],

            'id': ['com.dywx.larkplayer:id/mv'],
            # 'idx': [32, 34, 35]
            'idx': [],
            'content': []
        }

        # 页面黑名单  在遍历循环的一开始进行过滤
        self.black_screen_list = {
            '0': [''],
            '1': ['']
        }

        # 控制activity的最大数量
        self.act_max_count = {'me.sheimi.sgit.activities.explorer.ImportRepositoryActivity': 1,
                              'me.sheimi.sgit.activities.explorer.ExploreFileActivity': 1,
                              'me.sheimi.sgit.activities.explorer.ExploreRootDirActivity': 1}

        # activity黑名单
        self.black_act_list = []

        self.log_dir = self.path + '/' + 'result'

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # 最后需要保存的模型
        self.model = None

        # 初始化日志
        # 通过以下方式设置编码
        file_handler = logging.FileHandler(self.log_dir + '/' + 'log.txt', encoding='utf-8')
        logging.basicConfig(level=logging.INFO, handlers={file_handler})

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
        # device.press.home()

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

    def save_screen(self, screen):
        """
        保存页面信息
        :return:
        """

        sub_dir = self.path + '/' + screen.act_name + '-' + str(screen.id)
        if not os.path.exists(sub_dir):
            os.makedirs(sub_dir)

        device.dump(sub_dir + '/' + '1.xml', compressed=False)
        device.screenshot(sub_dir + '/' + '1.png')
        screen.shot_dir = sub_dir + '/' + '1.png'

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

    def add_screen(self, screen):
        """
        将新访问到的页面加入结果当中
        :return:
        """

        print('发现新界面')
        logging.info('发现新界面')
        self.screens[self.screen_id] = screen
        self.screen_id += 1
        if screen.act_name in self.act_count:
            self.act_count[screen.act_name] += 1
        else:
            self.act_count[screen.act_name] = 1

    def action_click(self, tmp_node):
        """
        对元素进行点击
        :param node:
        :return:
        """

        node_text = tmp_node.attrib['text']
        node_id = tmp_node.attrib['resource-id']
        node_content = tmp_node.attrib['content-desc']
        click_flag = True

        for text in self.black_elem_list['text']:
            if text in node_text.lower():
                click_flag = False

        for res_id in self.black_elem_list['id']:
            if res_id in node_id:
                click_flag = False

        for content in self.black_elem_list['content']:
            if content in node_content:
                click_flag = False

        for idx in self.black_elem_list['idx']:
            if idx == tmp_node.idx:
                click_flag = False

        if click_flag:
            x, y = tmp_node.get_click_position()
            device.click(x, y)

            print('当前点击元素')
            print(tmp_node.attrib)
            logging.info('当前点击元素')
            logging.info(tmp_node.attrib)
        else:
            print('黑名单元素 不予点击')
            print(tmp_node.attrib)
            logging.info('黑名单元素 不予点击')
            logging.info(tmp_node.attrib)

    def search_screen_transfer(self, screen, screen_sequences, des_id):
        """
        搜索所有到达目标screen的转移路线 使用递归实现的深度优先搜索
        :param des_id: 目标页面id
        :param screen_sequences: 页面转换序列
        :param screen:  起始搜索页面
        :return:
        """

        # 如果已经不能够再转移
        if screen.id == des_id:
            screen_sequences.append(screen.id)
            if screen_sequences not in screen.all_transfer_sequences:
                screen.all_transfer_sequences.append(screen_sequences)
            return

        # 将当前的页面加入screen_sequences
        screen_sequences.append(screen.id)

        # 遍历可以到达的des 并且继续递归的寻找
        for screen_id in screen.des:
            # 与c++不同 这里必须使用拷贝 否则传递的是list对象本身
            tmp_screen_sequences = screen_sequences.copy()
            # 避免有环
            if screen_id not in screen_sequences:
                self.search_screen_transfer(self.screens[screen_id], tmp_screen_sequences, des_id)

    def search_screen_transfer_3(self, source_id, des_id):
        """
        搜索一条到达目标screen的转移路线 使用迭代实现的深度优先搜索
        :param source_id:
        :param des_id:
        :return:
        """

        stack = Stack()
        stack.push(source_id)

        while not stack.empty():
            screen = self.screens[stack.top()]

            # 搜索已达目标页面
            if screen.id == des_id:
                # 把所有栈中元素取出
                screen_transfer = stack.items.copy()
                screen.all_transfer_sequences.append(screen_transfer)
                # 元素出栈 事件序列回退
                stack.pop()
            else:
                if screen.des != screen.visited_des:
                    for d_id in screen.des:
                        if d_id not in screen.visited_des:
                            screen.visited_des.append(d_id)
                            if d_id not in stack.items:
                                # 元素进栈
                                stack.push(d_id)
                                # 为了模拟 递归操作 此处应break
                                break
                else:
                    # 元素出栈 事件序列回退
                    stack.pop()
                    # 以下访问过的页面清空
                    screen.visited_des = []

    def screen_to_edge_transfer(self, screen_id_list):
        """
        通过screen的转换找出边的转换 这个可能是一条长边 未必是相邻的
        :return:
        """

        try:
            edges = []
            # 首先遍历页面的转换，然后找出它们之间可用的边，并加入到edge列表当中
            for i in range(len(screen_id_list) - 1):
                source_id = screen_id_list[i]
                des_id = screen_id_list[i + 1]

                tmp_list = []
                # 遍历所有的边去找到一条这样相邻的转移 但是结果可能有多个
                for edge in self.edges:
                    if edge.begin_id == source_id and edge.end_id == des_id:
                        tmp_list.append(edge)

                final_list = []
                # 尝试找出一条操作元素信息尽可能完全的边
                for edge in tmp_list:
                    target_screen = self.screens[edge.begin_id]
                    # 找回这个操作的元素
                    flag = False
                    for node in target_screen.nodes:
                        if node.idx == edge.node_id:
                            if node.attrib['resource-id'] != '' or \
                                    node.attrib['text'] != '' or \
                                    node.attrib['content-desc'] != '':
                                flag = True
                                break

                    if flag:
                        final_list.append(edge)

                if not final_list:
                    edges.append(tmp_list[0])
                else:
                    edges.append(final_list[0])

            return edges
        except Exception as e:
            print(e)
            for edge in self.edges:
                print('-----')
                print('source')
                print(edge.begin_id)
                print('des')
                print(edge.end_id)
                print('node_id')
                print(edge.node_id)
            exit(0)

    def register_watchers(self):
        """
        注册监听器
        :return:
        """

        # 注册watcher 去关闭弹窗 (目前只能解决那种打开应用的弹窗问题 无法解决应用持续弹窗 uiautomator2中才支持）
        device.watcher('CANCEL').when(text='取消').click(text='取消')
        device.watcher('CLOSE').when(text='关闭').click(text='关闭')
        device.watcher('LATER').when(text='Later').click(text='Later')
        device.watcher('UNDERSTOOD').when(text='Understood').click(text='Understood')
        device.watcher('CANSEL1').when(text='cancel').click(text='cancel')
        device.watcher('CANSEL2').when(text='Cancel').click(text='Cancel')
        device.watcher('CANSEL3').when(text='CANCEL').click(text='CANCEL')

    def reopen_app(self):
        """
        重新打开app
        :return:
        """

        self.close_app()
        self.open_app()
        time.sleep(5)

        # 触发一次监听器
        device.watchers.run()

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

    def replay_to_screen(self, screen):
        """
        通过重放到达页面状态
        最短路径应该是从边的集合中搜索而来
        :param screen:
        :return:
        """

        print('重放页面id')
        print(screen.id)

        logging.info('重放页面id')
        logging.info(screen.id)

        self.reopen_app()

        if not self.reopen_to_first:
            # 判断是否能够到达初始状态
            tmp_screen = self.get_tmp_screen()
            exist_screen_id = self.has_same_screen(tmp_screen)

            if exist_screen_id != 1:
                print('重新打开app无法回到第一个页面 需要点击back进行回退')
                logging.info('重新打开app无法回到第一个页面 需要点击back进行回退')
                try_back_times = 0
                # 有的app可以一直回退到关闭 但是有的app不行 会一直处于那个页面
                while exist_screen_id != 1 and not self.is_at_desktop():
                    try_back_times += 1
                    if try_back_times >= len(self.screens):
                        print('尝试回退次数大于最大次数')
                        logging.info('尝试回退次数大于最大次数')
                        print('回退初始状态失败 故不能进行重放')
                        logging.info('回退初始状态失败 故不能进行重放')
                        return False

                    print('尝试回退到初始状态...')
                    logging.info('尝试回退到初始状态...')
                    device.press.back()

                    time.sleep(5)
                    tmp_screen = self.get_tmp_screen()
                    exist_screen_id = self.has_same_screen(tmp_screen)

            if exist_screen_id == 1:
                print('回退初始状态成功')
                logging.info('回退初始状态成功')
            else:
                print('back 回到了桌面')
                print('需重新打开app')
                logging.info('back 回到了桌面')
                logging.info('需重新打开app')

                self.reopen_app()

                tmp_screen = self.get_tmp_screen()
                exist_screen_id = self.has_same_screen(tmp_screen)
                if exist_screen_id == 1:
                    print('回退初始状态成功')
                    logging.info('回退初始状态成功')
                else:
                    print('回退初始状态失败 故不能进行重放')
                    logging.info('回退初始状态失败 故不能进行重放')
                    return False

        # 如果是第一个页面需要重放 那么只要关闭再打开即可
        if screen.id == 1:
            return True

        # 所有的页面转移序列 可能有多条
        seq = []
        if not screen.shortest_transfer_sequences:
            print('需搜索最短重放序列')
            logging.info('需搜索最短重放序列')

            self.search_screen_transfer_3(self.screens[1].id, screen.id)
            print('重放页面转移序列')
            print(screen.all_transfer_sequences)
            logging.info('重放页面转移序列')
            logging.info(str(screen.all_transfer_sequences))
            # exit(0)

            try:
                # 找出最短的一条 页面转移序列
                seq = screen.all_transfer_sequences[0]
                min_len = len(seq)
                for id_list in screen.all_transfer_sequences:
                    if len(id_list) < min_len:
                        min_len = len(id_list)
                        seq = id_list
                print('搜索到的最短转移序列')
                print(seq)
                logging.info(' 重放页面转移序列')
                logging.info(str(seq))
                screen.shortest_transfer_sequences = seq
            except Exception as e:
                print(e)
                print('整个图转移的情况')
                logging.info(e)
                logging.info('整个图转移的情况')
                for s_id in self.screens:
                    screen = self.screens[s_id]
                    print('------------')
                    print('source')
                    print(s_id)
                    print('des')
                    logging.info('------------')
                    logging.info('source')
                    logging.info(s_id)
                    logging.info('des')
                    for d_id in screen.des:
                        print(d_id)
                        logging.info(d_id)

        else:
            seq = screen.shortest_transfer_sequences
            print('已有最短转移序列')
            print(seq)
            logging.info('已有最短转移序列')
            logging.info(seq)

        # 用页面转移去得到边的转移
        edges = self.screen_to_edge_transfer(seq)
        # 找到最短的边之后 进行重放
        print('replay--begin')
        logging.info('replay--begin')

        replay_flag = True
        try_times = 1
        while True:
            time.sleep(5)
            for edge in edges:
                begin_id = edge.begin_id
                clicked_node_id = edge.node_id
                screen = self.screens[begin_id]

                clicked_node = None
                for node in screen.nodes:
                    if node.idx == clicked_node_id:
                        clicked_node = node
                        break

                # 对该元素进行点击
                self.action_click(clicked_node)
                time.sleep(10)
                end_id = edge.end_id
                # 对页面状态进行检查
                if not self.check_for_cur_state(end_id):
                    # 表示有某条边重放失败
                    replay_flag = False
                    print('重放失败')
                    logging.info('重放失败')
                    break

            # 如果全部正确 则停止重放
            if replay_flag:
                break
            else:
                print('重放次数')
                print(try_times)
                logging.info('重放次数')
                logging.info(str(try_times))
                # 重新打开app
                if try_times >= self.replay_try_times:
                    # 如果重放了3次仍然失败 那么当前页面退栈
                    print('停止对该页面的重放')
                    logging.info('停止对该页面的重放')
                    return False
                self.reopen_app()
                try_times += 1

        print('replay--end')
        logging.info('replay--end')
        return True

    def check_for_cur_state(self, screen_id):
        """
        对当前的页面状态进行检查
        如果页面不对 则需要进行重放
        :return:
        """

        time.sleep(10)

        # 状态检查
        xml_info = device.dump(compressed=False)
        root = xeTree.fromstring(xml_info)
        nodes = parse_nodes(root)
        act_name = self.get_activity_name()
        tmp_screen = Screen(nodes, -1, act_name)
        screen = self.screens[screen_id]

        if not is_same_screen(tmp_screen, screen, self.distinct_rate):

            print('状态不一致 或需要重放')
            logging.info('状态不一致 或需要重放')

            print('dynamic visited')
            logging.info('dynamic visited')
            dynamic_visited = ''
            for node in tmp_screen.nodes:
                if node.attrib['text'] != '':
                    dynamic_visited += node.attrib['text']
            print(dynamic_visited)
            logging.info(str(dynamic_visited))
            print('saved')
            logging.info('saved')
            saved = ''
            for node in screen.nodes:
                if node.attrib['text'] != '':
                    saved += node.attrib['text']
            print(saved)
            logging.info(saved)

            return False

        return True

    def is_at_desktop(self):
        """
        判断应用是否在桌面状态
        :return:
        """

        xml_info = device.dump(compressed=False)
        root = xeTree.fromstring(xml_info)
        nodes = parse_nodes(root)

        for node in nodes:
            if '小工具' in node.attrib['text']:
                return True

        return False

    def run(self):
        """
        算法主函数
        :return:
        """

        self.start_time = time.time()
        # 注册监听器
        self.register_watchers()

        # 获取包名后 重新关闭并打开app
        self.reopen_app()

        # 获取当前页面信息
        xml_info = device.dump(compressed=False)
        root = xeTree.fromstring(xml_info)
        nodes = parse_nodes(root)
        act_name = self.get_activity_name()
        screen = Screen(nodes, self.screen_id, act_name)

        # 加入新页面
        self.cur_screen_id = self.screen_id

        # 页面id进栈
        self.stack.push(self.screen_id)

        self.add_screen(screen)

        # 保存初始页面
        self.save_screen(screen)

        # 用非递归实现深度优先搜索
        while not self.stack.empty():

            print('整个图转移的情况')
            logging.info('整个图转移的情况')
            for s_id in self.screens:
                screen = self.screens[s_id]
                print('------------')
                print('source')
                print(s_id)
                print('des')
                logging.info('------------')
                logging.info('source')
                logging.info(s_id)
                logging.info('des')
                for d_id in screen.des:
                    print(d_id)
                    logging.info(d_id)

            # 设置的遍历时间到
            if self.cost_time > self.max_time:
                print('时间到')
                print(self.cost_time)
                logging.info('时间到')
                logging.info(self.cost_time)
                break

            # 如果到达最大深度或是当前页面的所有元素都点击过
            cur_screen = self.screens[self.cur_screen_id]
            self.cur_depth = self.stack.size()
            # self.clicked_node = cur_screen.get_clickable_node()
            self.clicked_node = cur_screen.get_clickable_leaf_node(self.black_elem_list)

            if cur_screen.act_name in self.act_max_count:
                print('当前activity不再进行访问')
                logging.info('当前activity不再进行访问')

                print('退栈前栈顶元素为')
                print(self.stack.top())
                print(self.stack.items)

                logging.info('退栈前栈顶元素为')
                logging.info(self.stack.top())
                logging.info(str(self.stack.items))

                # 退栈 并更新当前页面
                self.stack.pop()
                print('退栈后栈顶元素为')
                print(self.stack.top())
                print(self.stack.items)

                logging.info('退栈后栈顶元素为')
                logging.info(self.stack.top())
                logging.info(self.stack.items)

                if self.stack.empty():
                    break

                self.cur_screen_id = self.stack.top()

                # 设备页面进行回退
                device.press.back()
                print('点击back')
                logging.info('点击back')
                continue

            print('当前深度')
            print(self.cur_depth)
            print('当前页面')
            print(self.cur_screen_id)

            logging.info('当前深度')
            logging.info(self.cur_depth)
            logging.info('当前页面')
            logging.info(self.cur_screen_id)

            # 如果栈空 且没有点击元素 那么停止
            if self.stack.empty() and self.clicked_node is None:
                break

            # 如果到达最大深度或是当前页面的所有元素都点击过
            if self.cur_depth >= self.max_depth or self.clicked_node is None:

                print('退栈前栈顶元素为')
                print(self.stack.top())
                print(self.stack.items)

                logging.info('退栈前栈顶元素为')
                logging.info(self.stack.top())
                logging.info(str(self.stack.items))

                # 退栈 并更新当前页面
                self.stack.pop()
                print('退栈后栈顶元素为')
                print(self.stack.top())
                print(self.stack.items)

                logging.info('退栈后栈顶元素为')
                logging.info(self.stack.top())
                logging.info(self.stack.items)

                if self.stack.empty():
                    break

                self.cur_screen_id = self.stack.top()

                # 设备页面进行回退
                device.press.back()
                print('点击back')
                logging.info('点击back')


            else:
                success = True
                if not self.check_for_cur_state(cur_screen.id):
                    # 使用重放技术到达需要回退的页面 可以尝试尽可能地使用back
                    success = self.replay_to_screen(cur_screen)

                if success:

                    # 对该元素进行点击
                    self.action_click(self.clicked_node)
                    time.sleep(10)

                    # 创建临时screen 判别是否发生页面切换
                    tmp_screen = self.get_tmp_screen()
                    exist_screen_id = self.has_same_screen(tmp_screen)
                    # 如果发生了页面切换
                    if exist_screen_id != self.cur_screen_id:

                        # 如果不是发现了新界面
                        if exist_screen_id != -1:
                            print('已有相同界面')
                            print(exist_screen_id)

                            logging.info('已有相同界面')
                            logging.info(exist_screen_id)

                            # 记录页面之间的转移
                            if exist_screen_id not in self.screens[self.cur_screen_id].des:
                                self.screens[self.cur_screen_id].des.append(exist_screen_id)
                            # 记录边的转移
                            print('页面的转移')
                            print('source')
                            print(self.cur_screen_id)
                            print('des')
                            print(exist_screen_id)

                            logging.info('页面的转移')
                            logging.info('source')
                            logging.info(self.cur_screen_id)
                            logging.info('des')
                            logging.info(exist_screen_id)

                            # 按照id来过滤边
                            if not has_same_edge(self.screens, self.edges,
                                                 self.cur_screen_id, exist_screen_id, self.clicked_node):
                                edge = Edge(self.cur_screen_id, exist_screen_id, self.clicked_node.idx)
                                self.edges.append(edge)

                            # 页面已经已经有了 也是需要回退的
                            device.press.back()
                            print('点击back')
                            logging.info('点击back')


                        else:
                            # 发现了新界面
                            tmp_screen.id = self.screen_id
                            tmp_package_name = get_package_name()
                            if tmp_package_name == self.package_name:
                                add_screen_flag = True
                                if tmp_screen.act_name in self.black_act_list:
                                    print('activity 在黑名单内 不保存页面')
                                    logging.info('activity 在黑名单内 不保存页面')
                                    add_screen_flag = False

                                if tmp_screen.act_name in self.act_max_count and \
                                        tmp_screen.act_name in self.act_count and \
                                        self.act_count[tmp_screen.act_name] >= self.act_max_count[tmp_screen.act_name]:
                                    print('当前activity 保存的页面数已达最大限制')
                                    logging.info('当前activity 保存的页面数已达最大值')
                                    add_screen_flag = False

                                if add_screen_flag:
                                    # 加入页面
                                    self.add_screen(tmp_screen)
                                    edge = Edge(self.cur_screen_id, tmp_screen.id, self.clicked_node.idx)
                                    self.edges.append(edge)

                                    # 记录页面之间的转移
                                    self.screens[self.cur_screen_id].des.append(tmp_screen.id)

                                    print('页面的转移')
                                    print('source')
                                    print(self.cur_screen_id)
                                    print('des')
                                    print(tmp_screen.id)

                                    logging.info('页面的转移')
                                    logging.info('source')
                                    logging.info(self.cur_screen_id)
                                    logging.info('des')
                                    logging.info(tmp_screen.id)

                                    # 更新页面转移
                                    self.cur_screen_id = tmp_screen.id
                                    # 页面进栈
                                    self.stack.push(tmp_screen.id)
                                    print('进栈')
                                    print('此时栈顶元素为')
                                    print(self.stack.top())
                                    print(self.stack.items)

                                    logging.info('进栈')
                                    logging.info('此时栈顶元素为')
                                    logging.info(str(self.stack.top()))
                                    logging.info(str(self.stack.items))

                                    # 保存页面信息
                                    self.save_screen(tmp_screen)

                            else:
                                print('跳出了应用 不保存应用外的页面')
                                logging.info('跳出了应用 不保存应用外的页面')

                    else:
                        print('页面未发生转换')
                        print('不记录此操作')

                        logging.info('页面未发生转换')
                        logging.info('不记录此操作')

                else:
                    print('退栈前栈顶元素为')
                    print(self.stack.top())
                    print(self.stack.items)

                    logging.info('退栈前栈顶元素为')
                    logging.info(self.stack.top())
                    logging.info(str(self.stack.items))

                    # 退栈 并更新当前页面
                    self.stack.pop()
                    print('退栈后栈顶元素为')
                    print(self.stack.top())
                    print(self.stack.items)

                    logging.info('退栈后栈顶元素为')
                    logging.info(self.stack.top())
                    logging.info(self.stack.items)

                    if self.stack.empty():
                        break

                    self.cur_screen_id = self.stack.top()

                    # 设备页面进行回退
                    device.press.back()
                    print('点击back')
                    logging.info('点击back')

                tmp_time = time.time()
                self.cost_time = tmp_time - self.start_time

        # 遍历完成后 打印遍历结果 source_id-des_id: 所有的边的信息
        for s_id in self.screens.keys():
            screen = self.screens[s_id]
            print('当前页面id为' + str(s_id))
            logging.info('当前页面id为' + str(s_id))
            for d_id in screen.des:
                print('edges:')
                logging.info('edges:')
                for edge in self.edges:
                    if edge.begin_id == s_id and edge.end_id == d_id:
                        print('source_id:' + str(s_id))
                        print('des_id:' + str(d_id))
                        print('---edge---')
                        print('clicked node id:' + str(edge.node_id))

                        logging.info('source_id:' + str(s_id))
                        logging.info('des_id:' + str(d_id))
                        logging.info('---edge---')
                        logging.info('clicked node id:' + str(edge.node_id))

                        clicked_node = screen.get_node_by_id(edge.node_id)
                        print(clicked_node.attrib)
                        logging.info(clicked_node.attrib)
            print('---------------------------------------------')
            logging.info('---------------------------------------------')

        # 记录花费的总时间
        tmp_time = time.time()
        self.cost_time = tmp_time - self.start_time
        logging.info('总花费时间：' + str(self.cost_time))

        # 记录交互组件总数
        clicked_node_num = 0
        for key in self.screens.keys():
            screen = self.screens[key]
            clicked_node_num += len(screen.has_clicked_nodes)

        logging.info('总交互组件数量：' + str(clicked_node_num))

        # 记录总activity数
        logging.info('Activity数量：' + str(len(self.act_count)))

        # 记录总页面数
        logging.info('页面数量：' + str(len(self.screens)))

        # 记录总边数
        logging.info('边的数量：' + str(len(self.edges)))

        save_dir = self.path + '/' + 'result'
        # 直接将screens和边存储为model的模式
        self.model = GUIModel(self.screens, self.edges)
        model = pickle.dumps(self.model)
        with open(save_dir + '/model', 'wb') as f:
            f.write(model)

        visual_obj = VisualTool(self.screens, self.edges, save_dir)
        visual_obj.save_work()

    def manual(self):

        dir = 'C:/Users/dell/Desktop/tmp'
        device.dump(dir + "/" + "" + 'StageFever.xml', compressed=False)
        device.screenshot(dir + "/" + 'StageFever' + '.png')


def get_package_name():
    """
    初始获得包名
    初始获取包名可以从Manifest文件中获取
    还有一种获取包名的方法是 先dump 然后查看节点信息
    return:
    """

    try:
        cmd = "adb shell \"dumpsys window w | grep name=\""
        r = os.popen(cmd)
        info = r.readlines()

        for i in range(len(info)):
            if 'Activity' in info[i]:
                package_name = info[i].strip().split('/')[0].split('name=')[1]
                break
            else:
                if 'mumu' not in info[i] and 'systemui' not in info[i] and '/' in info[i]:
                    package_name = info[i].strip().split('/')[0].split('name=')[1]
                    break

        return package_name
    except Exception as e:
        return 'error package name'


if __name__ == '__main__':
    package_name = get_package_name()
    save_dir = 'E:/graduation/scrob_experiment/traverse_compare/Dianping/10.26/runner'
    obj = Crawler(package_name, save_dir)
    obj.run()
