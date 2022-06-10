import os
import cv2
from graphviz import Digraph


class VisualTool:
    """
    一个用于对应用页面图生成可视化图片的工具类
    主要使用graphviz实现
    用不同颜色标记变化的页面和边
    """

    def __init__(self, screens, edges, work_dir, version):
        self.dot = Digraph(comment='The Round Table')

        # screen和边 其实对应的就是边和节点
        self.screens = screens

        self.edges = edges

        self.work_dir = work_dir

        self.save_dir = self.work_dir + '/' + 'result'

        self.version = version

    def create_nodes(self):
        """
        使用screen创建图中的节点
        :return:
        """

        for key in self.screens.keys():
            screen = self.screens[key]

            if self.version == 0:
                img_path = self.work_dir + '/' + 'base_screens' + '/' + str(screen.id) + '.png'
            else:
                img_path = self.work_dir + '/' + 'updated_screens' + '/' + str(screen.id) + '.png'

            # print(img_path)

            # 图片版本
            # 首先读取图片
            img = cv2.imread(img_path)

            small_img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

            if self.version == 0:
                img_dir = self.save_dir + '/' + 'baseimage'
            else:
                img_dir = self.save_dir + '/' + 'updatedimage'

            if not os.path.exists(img_dir):
                os.makedirs(img_dir)

            cv2.imwrite(img_dir + '/' + str(screen.id) + '.png', small_img)

            if screen.matched_id == -1:
                self.dot.node(str(screen.id), shapefile=img_dir + '/' + str(screen.id) + '.png',
                              label=str(screen.id) + 'no matched', fontcolor='red', fontsize='30')
            else:
                self.dot.node(str(screen.id), shapefile=img_dir + '/' + str(screen.id) + '.png', fontsize='30')

    def create_edges(self):
        """
        使用edges创建图中的边
        :return:
        """

        for edge in self.edges:
            node_id = edge.node_id
            clickable_node = self.screens[edge.begin_id].get_node_by_id(node_id)
            if clickable_node.attrib['text'] != '':
                label = clickable_node.attrib['text'] + '-' + clickable_node.attrib['bounds']
            elif clickable_node.attrib['content-desc'] != '':
                label = clickable_node.attrib['content-desc'] + '-' + clickable_node.attrib['bounds']
            elif clickable_node.attrib['resource-id'] != '':
                label = clickable_node.attrib['resource-id'].split('/')[1] + '-' + clickable_node.attrib['bounds']
            else:
                label = clickable_node.attrib['bounds']
            # label = clickable_node.attrib['bounds']

            label = label + 'id:' +  str(edge.id)

            if edge.matched_id == -1:
                self.dot.edge(str(edge.begin_id), str(edge.end_id), label=label, fontname='SimSun', color='red',
                              fontsize='30')
            else:
                self.dot.edge(str(edge.begin_id), str(edge.end_id), label=label, fontname='SimSun', fontsize='30')

    def save_graph(self):
        """
        对图片的结果进行保存
        :return:
        """

        if self.version == 0:
            self.dot.render(filename='base_graph', directory=self.save_dir, view=True)
        else:
            self.dot.render(filename='updated_graph', directory=self.save_dir, view=True)

    def save_work(self):
        """
        创建图并保存
        :return:
        """

        self.create_nodes()
        self.create_edges()
        self.save_graph()
