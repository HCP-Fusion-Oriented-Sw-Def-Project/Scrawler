import os

import cv2
from graphviz import Digraph


# # 第一种保存图片的方式 首先直接打开网页进行展示 然后会保存
# dot.view()

# 第二种保存图片的方式 将图片保存至指定路径 如果view=True 则同时也会触发第一种保存方式
# dot.render(filename='traverse_graph', directory='result', view=False)


class VisualTool:
    """
    一个用于对应用页面图生成可视化图片的工具类
    主要使用graphviz实现
    """

    def __init__(self, screens, edges, save_dir):
        self.dot = Digraph(comment='The Round Table')

        # screen和边 其实对应的就是边和节点
        self.screens = screens

        self.edges = edges

        self.save_dir = save_dir

    def create_nodes(self):
        """
        使用screen创建图中的节点
        :return:
        """

        for key in self.screens.keys():
            screen = self.screens[key]

            # 图片版本
            # 首先读取图片
            img = cv2.imread(screen.shot_dir)
            small_img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

            img_dir = self.save_dir + '/' + 'image'

            if not os.path.exists(img_dir):
                os.makedirs(img_dir)

            cv2.imwrite(img_dir + '/' + str(screen.id) + '.png', small_img)

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
            self.dot.edge(str(edge.begin_id), str(edge.end_id), label=label, fontname='SimSun', fontsize='30')


    def save_graph(self):
        """
        对图片的结果进行保存
        :return:
        """

        self.dot.render(filename='traverse_graph2', directory=self.save_dir, view=True)

    def save_work(self):
        """
        创建图并保存
        :return:
        """

        self.create_nodes()
        self.create_edges()
        self.save_graph()
