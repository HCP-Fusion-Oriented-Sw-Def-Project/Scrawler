import os
import pickle
import cv2

from utility import get_screen_sim, is_xpath_matched, get_elem_distance, is_sim, get_str_sim
from visualize import VisualTool


class Comparator:
    """
    比较器类
    用于对模型进行比较
    """

    def __init__(self, work_dir):
        # 基础版本的模型 以及更新版本的模型
        self.base_model = None
        self.updated_model = None

        # 获取模型的路径
        self.work_dir = work_dir

        # # 页面搜集
        self.removed_screens = []

        self.added_screens = []

        # 页面映射 专用于对匹配的页面进行映射
        self.screens_map = {}

        # 相似度阈值
        self.text_sim = 0.5

        # 初始化日志
        # 通过以下方式设置编码
        self.result_dir = self.work_dir + '/' + 'result'

        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

    def read_model(self):
        """
        从路径中读取模型
        :return:
        """

        f = open(self.work_dir + '/base_model', 'rb')
        self.base_model = pickle.load(f)
        f = open(self.work_dir + '/updated_model', 'rb')
        self.updated_model = pickle.load(f)

        # 初始化页面的匹配id 以及边的id和匹配id 因为边本身没有id
        for key in self.base_model.screens:
            self.base_model.screens[key].matched_id = -1

        for key in self.updated_model.screens:
            self.updated_model.screens[key].matched_id = -1

        for i in range(len(self.base_model.edges)):
            self.base_model.edges[i].id = i + 1

        for i in range(len(self.updated_model.edges)):
            self.updated_model.edges[i].id = i + 1

        for edge in self.base_model.edges:
            edge.matched_id = -1

        for edge in self.updated_model.edges:
            edge.matched_id = -1

        # 将所有的screen转到当前文件夹下
        base_screen_dir = self.work_dir + '/' + 'base_screens'
        updated_screen_dir = self.work_dir + '/' + 'updated_screens'

        if not os.path.exists(base_screen_dir):
            os.makedirs(base_screen_dir)

        if not os.path.exists(updated_screen_dir):
            os.makedirs(updated_screen_dir)

        for key in self.base_model.screens:
            screen = self.base_model.screens[key]
            img = cv2.imread(screen.shot_dir)
            cv2.imwrite(base_screen_dir + '/' + str(screen.id) + '.png', img)

        for key in self.updated_model.screens:
            screen = self.updated_model.screens[key]
            img = cv2.imread(screen.shot_dir)
            cv2.imwrite(updated_screen_dir + '/' + str(screen.id) + '.png', img)

    def map_for_screens(self):
        """
        进行页面映射
        :return:
        """

        for x_key in self.base_model.screens.keys():
            base_screen = self.base_model.screens[x_key]

            max_score = 0
            matched_screen = None
            # 去找到与它相似度最大的页面
            for y_key in self.updated_model.screens.keys():
                tmp_screen = self.updated_model.screens[y_key]
                if tmp_screen.matched_id == -1:
                    sim_score = get_screen_sim(base_screen, tmp_screen)
                    if sim_score >= self.text_sim and sim_score > max_score:
                        max_score = sim_score
                        matched_screen = tmp_screen

            if matched_screen is not None:
                base_screen.matched_id = matched_screen.id
                matched_screen.matched_id = base_screen.id

        # 然后查看页面的匹配结果
        for key in self.base_model.screens:
            screen = self.base_model.screens[key]
            if screen.matched_id == -1:
                self.removed_screens.append(screen.id)

        for key in self.base_model.screens:
            screen = self.base_model.screens[key]
            if screen.matched_id != -1:
                self.screens_map[screen.id] = screen.matched_id

        for key in self.updated_model.screens:
            screen = self.updated_model.screens[key]
            if screen.matched_id == -1:
                self.added_screens.append(screen.id)

    def map_for_edges(self):
        """
        进行边的映射
        感觉这个结果需要把元素圈出来 不然很难看
        先把整体的可视化结果给出 然后在把这些边转移的元素圈出来
        :return:
        """

        # 先给可以用xpath进行映射的边 进行映射
        for edge in self.base_model.edges:
            if edge.begin_id not in self.removed_screens and edge.end_id not in self.removed_screens:
                # 首先映射成新版本的边
                updated_begin_id = self.screens_map[edge.begin_id]
                updated_end_id = self.screens_map[edge.end_id]

                # 然后开始查找新版本的边当中的映射
                for u_edge in self.updated_model.edges:
                    if u_edge.begin_id == updated_begin_id and \
                            u_edge.end_id == updated_end_id and \
                            u_edge.matched_id == -1:
                        # 那么考虑元素是否可以映射上
                        b_node = self.base_model.screens[edge.begin_id].get_node_by_id(edge.node_id)
                        u_node = self.updated_model.screens[updated_begin_id].get_node_by_id(u_edge.node_id)

                        if is_xpath_matched(b_node, u_node):
                            edge.matched_id = u_edge.id
                            u_edge.matched_id = edge.id
                            break

        # 然后使用文本距离的方法 再找一次
        for edge in self.base_model.edges:
            if edge.begin_id not in self.removed_screens and edge.end_id not in self.removed_screens:
                # 首先映射成新版本的边
                updated_begin_id = self.screens_map[edge.begin_id]
                updated_end_id = self.screens_map[edge.end_id]

                matched_edge = None
                max_sim = 0

                # 那么考虑元素是否可以映射上
                b_node = self.base_model.screens[edge.begin_id].get_node_by_id(edge.node_id)

                # 然后开始查找新版本的边当中的映射
                for u_edge in self.updated_model.edges:
                    if u_edge.begin_id == updated_begin_id and \
                            u_edge.end_id == updated_end_id and \
                            u_edge.matched_id == -1:
                        u_node = self.updated_model.screens[updated_begin_id].get_node_by_id(u_edge.node_id)

                        sim = get_str_sim(b_node, u_node)
                        if sim > max_sim:
                            max_sim = sim
                            matched_edge = u_edge

                if matched_edge is not None:
                    if max_sim >= 0.5:
                        edge.matched_id = matched_edge.id
                        matched_edge.matched_id = edge.id

        # 然后使用距离的方法 再找一次
        for edge in self.base_model.edges:
            if edge.begin_id not in self.removed_screens and edge.end_id not in self.removed_screens:
                # 首先映射成新版本的边
                updated_begin_id = self.screens_map[edge.begin_id]
                updated_end_id = self.screens_map[edge.end_id]

                matched_edge = None
                min_dist = 100000
                # 那么考虑元素是否可以映射上
                b_node = self.base_model.screens[edge.begin_id].get_node_by_id(edge.node_id)
                # 然后开始查找新版本的边当中的映射
                for u_edge in self.updated_model.edges:
                    if u_edge.begin_id == updated_begin_id and \
                            u_edge.end_id == updated_end_id and \
                            u_edge.matched_id == -1:

                        u_node = self.updated_model.screens[updated_begin_id].get_node_by_id(u_edge.node_id)
                        dist = get_elem_distance(b_node, u_node)
                        if dist < min_dist:
                            matched_edge = u_edge
                            min_dist = dist

                if matched_edge is not None:
                    # 然后看最小的dist是否符合要求
                    m_node = self.updated_model.screens[updated_begin_id].get_node_by_id(matched_edge.node_id)

                    if is_sim(b_node, m_node):
                        edge.matched_id = matched_edge.id
                        matched_edge.matched_id = edge.id

    def get_screens_result_by_image(self):
        """
        直接使用图来可视化结果页面匹配结果
        :return:
        """

        # 创建文件夹
        screen_dir = self.result_dir + '/' + 'screens'
        removed_sdir = screen_dir + '/' + 'removed'
        matched_sdir = screen_dir + '/' + 'matched'
        added_sdir = screen_dir + '/' + 'added'

        dir_list = [removed_sdir, matched_sdir, added_sdir]

        for path in dir_list:
            if not os.path.exists(path):
                os.makedirs(path)

        # 搜集页面图片
        for key in self.base_model.screens:
            screen = self.base_model.screens[key]
            img_path = self.work_dir + '/' + 'base_screens' + '/' + str(screen.id) + '.png'
            # 首先读取图片
            img = cv2.imread(img_path)
            if screen.matched_id == -1:
                cv2.imwrite(removed_sdir + '/' + str(screen.id) + '.png', img)

            else:
                # 表示匹配上了
                m_screen = self.updated_model.screens[screen.matched_id]
                m_img_path = self.work_dir + '/' + 'updated_screens' + '/' + str(m_screen.id) + '.png'
                m_img = cv2.imread(m_img_path)
                cv2.imwrite(matched_sdir + '/' + str(screen.id) + '-' + str(m_screen.id) + '.png', img)
                cv2.imwrite(matched_sdir + '/' + str(screen.id) + '-' + str(m_screen.id) + 'm.png', m_img)

        for key in self.updated_model.screens:
            screen = self.updated_model.screens[key]
            img_path = self.work_dir + '/' + 'updated_screens' + '/' + str(screen.id) + '.png'
            if screen.matched_id == -1:
                # 首先读取图片
                img = cv2.imread(img_path)
                cv2.imwrite(added_sdir + '/' + str(screen.id) + '.png', img)

    def get_edges_result_by_image(self):
        """
        直接使用图来可视化边的匹配结果
        :return:
        """

        # 创建文件夹
        edge_dir = self.result_dir + '/' + 'edges'
        removed_edir = edge_dir + '/' + 'removed'
        matched_edir = edge_dir + '/' + 'matched'
        added_edir = edge_dir + '/' + 'added'

        dir_list = [removed_edir, matched_edir, added_edir]

        for path in dir_list:
            if not os.path.exists(path):
                os.makedirs(path)

        for edge in self.base_model.edges:
            if edge.matched_id == -1:
                begin_id = edge.begin_id
                node = self.base_model.screens[begin_id].get_node_by_id(edge.node_id)

                tmp_dir = removed_edir + '/' + str(edge.id)
                if not os.path.exists(tmp_dir):
                    os.makedirs(tmp_dir)

                begin_img_path = self.work_dir + '/' + 'base_screens' + '/' + str(edge.begin_id) + '.png'
                end_img_path = self.work_dir + '/' + 'base_screens' + '/' + str(edge.end_id) + '.png'

                # 读取图片
                b_img = cv2.imread(begin_img_path)
                e_img = cv2.imread(end_img_path)

                # 然后在beign_img中画出 这个点击的节点
                x1, y1, x2, y2 = node.parse_bounds()
                cv2.rectangle(b_img, (x1, y1), (x2, y2), (0, 0, 255), 2)

                # 然后保存图片
                cv2.imwrite(tmp_dir + '/' + 'begin_img' + str(edge.begin_id) + '.png', b_img)
                cv2.imwrite(tmp_dir + '/' + 'end_img' + str(edge.end_id) + '.png', e_img)

            else:
                # 表示边匹配上了
                begin_id = edge.begin_id
                tmp_dir = matched_edir + '/' + str(edge.id) + '-' + str(edge.matched_id)

                if not os.path.exists(tmp_dir):
                    os.makedirs(tmp_dir)

                node = self.base_model.screens[begin_id].get_node_by_id(edge.node_id)
                begin_img_path = self.work_dir + '/' + 'base_screens' + '/' + str(edge.begin_id) + '.png'
                end_img_path = self.work_dir + '/' + 'base_screens' + '/' + str(edge.end_id) + '.png'
                # 读取图片
                b_img = cv2.imread(begin_img_path)
                e_img = cv2.imread(end_img_path)
                # 然后在beign_img中画出 这个点击的节点
                x1, y1, x2, y2 = node.parse_bounds()
                cv2.rectangle(b_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                # 然后保存图片
                cv2.imwrite(tmp_dir + '/' + 'begin_img' + str(edge.begin_id) + '.png', b_img)
                cv2.imwrite(tmp_dir + '/' + 'end_img' + str(edge.end_id) + '.png', e_img)

                # 获取匹配到的边 再按照如上方式保存
                m_edge = self.updated_model.edges[edge.matched_id - 1]
                m_node = self.updated_model.screens[m_edge.begin_id].get_node_by_id(m_edge.node_id)
                m_begin_img_path = self.work_dir + '/' + 'updated_screens' + '/' + str(m_edge.begin_id) + '.png'
                m_end_img_path = self.work_dir + '/' + 'updated_screens' + '/' + str(m_edge.end_id) + '.png'

                # 读取图片
                m_b_img = cv2.imread(m_begin_img_path)
                m_e_img = cv2.imread(m_end_img_path)

                # 然后在beign_img中画出 这个点击的节点
                x1, y1, x2, y2 = m_node.parse_bounds()
                cv2.rectangle(m_b_img, (x1, y1), (x2, y2), (0, 0, 255), 2)

                cv2.imwrite(tmp_dir + '/' + 'm_begin_img' + str(m_edge.begin_id) + '.png', m_b_img)
                cv2.imwrite(tmp_dir + '/' + 'm_end_img' + str(m_edge.end_id) + '.png', m_e_img)

        for edge in self.updated_model.edges:
            if edge.matched_id == -1:
                begin_id = edge.begin_id
                node = self.updated_model.screens[begin_id].get_node_by_id(edge.node_id)

                tmp_dir = added_edir + '/' + str(edge.id)
                if not os.path.exists(tmp_dir):
                    os.makedirs(tmp_dir)

                begin_img_path = self.work_dir + '/' + 'updated_screens' + '/' + str(edge.begin_id) + '.png'
                end_img_path = self.work_dir + '/' + 'updated_screens' + '/' + str(edge.end_id) + '.png'

                # 读取图片
                b_img = cv2.imread(begin_img_path)
                e_img = cv2.imread(end_img_path)

                # 然后在beign_img中画出 这个点击的节点
                x1, y1, x2, y2 = node.parse_bounds()
                cv2.rectangle(b_img, (x1, y1), (x2, y2), (0, 0, 255), 2)

                # 然后保存图片
                cv2.imwrite(tmp_dir + '/' + 'begin_img' + str(edge.begin_id) + '.png', b_img)
                cv2.imwrite(tmp_dir + '/' + 'end_img' + str(edge.end_id) + '.png', e_img)

    def work(self):
        self.read_model()
        self.map_for_screens()
        self.map_for_edges()

        base_obj = VisualTool(self.base_model.screens, self.base_model.edges, self.work_dir, 0)
        base_obj.save_work()
        updated_obj = VisualTool(self.updated_model.screens, self.updated_model.edges, self.work_dir, 1)
        updated_obj.save_work()

        self.get_screens_result_by_image()
        self.get_edges_result_by_image()


if __name__ == '__main__':
    obj = Comparator('C:/Users/dell/Desktop/tmp_comparisio')
    obj.work()
