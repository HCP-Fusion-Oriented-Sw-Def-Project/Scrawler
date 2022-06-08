class Edge:
    """
    GUI边类
    """

    def __init__(self, b_id, e_id, n_id):
        # 所在页面的编号 也是begin_id
        self.begin_id = b_id
        self.end_id = e_id
        # 所执行的操作 目前默认为click
        self.action = 'clicked'

        # 操作的元素
        self.node_id = n_id


def has_same_edge(screens, edges, begin_id, end_id, clicked_node):
    """
    用于判断边是否已经存在 使用id进行过滤
    :param edges:
    :param begin_id:
    :param end_id:
    :param clicked_node:
    :return:
    """

    if clicked_node.attrib['resource-id'] != '':
        for edge in edges:
            if edge.begin_id == begin_id and edge.end_id == end_id:
                screen = screens[begin_id]
                node = screen.get_node_by_id(edge.node_id)
                if node.attrib['resource-id'] == clicked_node.attrib['resource-id']:
                    return True

    return False

# class EventSequence:
#     """
#     事件序列类
#     """
#
#     def __init__(self):
#         # 边的集合
#         self.edges = []
