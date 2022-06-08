import logging


class Screen():
    """
    GUI页面类
    """

    def __init__(self, nodes, s_id, activity):
        # 所在的activity名字
        self.act_name = activity
        self.id = s_id
        # 到达该页面的事件序列
        self.event_sequences = []
        # 页面中的节点
        self.nodes = nodes
        # 已点击元素
        self.has_clicked_nodes = []

        # 第一次访问时所在的深度
        self.depth = -1

        # 能够到达的终点页面的列表
        self.des = []

        # 到达此页面的页面转移序列 无环 [[], [], ]
        self.all_transfer_sequences = []

        # 以下变量用于实现迭代实现深度优先搜索寻找页面转移

        # 一访问过的页面
        self.visited_des = []

        # 一条最短的重放边
        self.shortest_transfer_sequences = []

        # 图片存放的路径
        self.shot_dir = ''

        # 是否使用id进行过滤
        self.filter_id = False

        # id列表
        self.id_list = []

    def get_clickable_node(self):
        """
        获取可点击的元素
        :return:
        """

        clickable_nodes = []
        id_list = []
        for node in self.nodes:
            if not is_node_in_list(node, self.has_clicked_nodes) and \
                    node.attrib['clickable'] == 'true' and \
                    node.attrib['resource-id'] not in id_list:

                clickable_nodes.append(node)

        print('当前页面待点击数量' + str(len(clickable_nodes)))
        logging.info('当前页面待点击数量' + str(len(clickable_nodes)))

        if not clickable_nodes:
            return None
        else:
            #  在这里对点击元素进行了过滤
            self.has_clicked_nodes.append(clickable_nodes[0])
            return clickable_nodes[0]

    def get_clickable_leaf_node(self, black_elem_list):
        """
        获取可点击的元素 只获取叶子节点
        :param black_elem_list:
        :param self:
        :return:
        """

        clickable_nodes = []

        for node in self.nodes:
            if node.attrib['clickable'] == 'true':
                # num += 1
                # 如果本身为叶子节点
                if not node.children:
                    if not is_in_black_list(node, black_elem_list):
                        if not is_node_in_list(node, self.has_clicked_nodes) and not is_ignored_node(node) and \
                                node.attrib['resource-id'] not in self.id_list:
                            clickable_nodes.append(node)

                            # 只对不为空的id元素进行过滤
                            if node.attrib['resource-id'] != '' and self.filter_id is True:
                                self.id_list.append(node.attrib['resource-id'])
                else:
                    # 如果本身不为叶子节点
                    for desc in node.descendants:
                        # 某子孙节点为叶子节点
                        if not desc.children:
                            if not is_in_black_list(desc, black_elem_list):
                                if not is_node_in_list(desc, self.has_clicked_nodes) \
                                        and not is_ignored_node(desc) and \
                                        desc.attrib['resource-id'] not in self.id_list and \
                                        not is_node_in_list(desc, clickable_nodes):
                                    # 这里也要注意节点重复的问题 因为在有嵌套的情况下 可点击元素会少很多
                                    clickable_nodes.append(desc)

                                    # 只对不为空的id元素进行过滤
                                    if desc.attrib['resource-id'] != '' and self.filter_id is True:
                                        self.id_list.append(desc.attrib['resource-id'])

                                    # 在这里加个break可以过滤 触发相同转移的操作
                                    # break

        print('当前页面待点击数量' + str(len(clickable_nodes)))

        if not clickable_nodes:
            return None
        else:
            #  在这里对点击元素进行了过滤
            self.has_clicked_nodes.append(clickable_nodes[0])
            return clickable_nodes[0]

    def get_node_by_id(self, node_id):
        """
        在页面中通过id查找元素
        :param node_id:
        :return:
        """

        for node in self.nodes:
            if node.idx == node_id:
                return node

        return None


def is_ignored_node(node):
    """
    判断当前节点是否需要忽略
    :return:
    """

    if 'layout' in node.attrib['class'] or node.attrib['class'] == 'android.view.View':
        return True

    return False


class Stack():
    """
    实现一个栈 用于存储页面id
    """

    def __init__(self):
        self.items = []

    def push(self, num):
        """
        元素入栈
        :return:
        """

        self.items.append(num)

    def pop(self):
        """
        元素出栈
        :param num:
        :return:
        """

        return self.items.pop()

    def empty(self):
        """
        判断栈是否为空
        :return:
        """

        return self.items == []

    def top(self):
        """
        返回栈顶元素
        :return:
        """

        if self.items:
            return self.items[len(self.items) - 1]

        return -1

    def size(self):
        """
        获得栈的大小
        :return:
        """

        return len(self.items)


def is_same_screen(x_screen, y_screen, distinct_rate):
    if x_screen.act_name != y_screen.act_name:
        return False

    x_xpath_list = []
    y_xpath_list = []

    for node in x_screen.nodes:
        x_xpath_list.append(node.full_xpath)

    for node in y_screen.nodes:
        y_xpath_list.append(node.full_xpath)

    count = 0
    for xpath in x_xpath_list:
        if xpath in y_xpath_list:
            count += 1

    # 对于没有动态元素的app 这个页面判定相等必须要严格一点
    if count / max(len(x_xpath_list), len(y_xpath_list)) >= distinct_rate:
        return True

    return False


def is_node_in_list(tmp_node, node_list):
    """
    判断一个元素是否存在于列表当中
    :return:
    """

    for node in node_list:
        if tmp_node.idx == node.idx:
            return True

    return False


def is_in_black_list(tmp_node, black_elem_list):
    """
    判断一个元素是不是在黑名单中
    :param tmp_node:
    :param black_elem_list:
    :return:
    """

    node_text = tmp_node.attrib['text']
    node_id = tmp_node.attrib['resource-id']
    node_content = tmp_node.attrib['content-desc']
    is_black = False

    for text in black_elem_list['text']:
        if text in node_text:
            is_black = True

    for res_id in black_elem_list['id']:
        if res_id in node_id:
            is_black = True

    for content in black_elem_list['content']:
        if content in node_content:
            is_black = True

    for idx in black_elem_list['idx']:
        if idx == tmp_node.idx:
            is_black = True

    return is_black
