import Levenshtein
from str_utility import split_str, get_words_vector_by_tfidf, get_words_sim


def get_screen_sim(x_screen, y_screen):
    """
    获取两个页面的相似度 使用id/text/content-desc
    :param x_screen:
    :param y_screen:
    :return:
    """

    # activity name 不同 直接返回0
    # if x_screen.act_name != y_screen.act_name:
    #     print('activity不同')
    #     print(x_screen.act_name)
    #     print(y_screen.act_name)
    #     return 0

    # 用于记录 tfidf返回的词汇表（因为它会内部处理一些较短词汇 然后如果为空 我自己的处理是补全为none）
    xx_id_words = []
    xx_text_words = []
    xx_content_words = []

    yy_id_words = []
    yy_text_words = []
    yy_content_words = []

    # 首先分别搜集元素的 id text content-desc
    x_id = []
    x_text = []
    x_content = []

    for node in x_screen.nodes:
        if node.attrib['resource-id'] != '':
            if '_' not in node.attrib['resource-id'] and '/' in node.attrib['resource-id']:
                x_id.append(node.attrib['resource-id'].split('/')[1])
            elif '_' in node.attrib['resource-id'] and '/' in node.attrib['resource-id']:
                tmp_list = node.attrib['resource-id'].split('/')[1].split('_')
                x_id.extend(tmp_list)
            else:
                x_id.append(node.attrib['resource-id'])

        if node.attrib['text'] != '':
            x_text.append(node.attrib['text'].lower().strip())

        if node.attrib['content-desc'] != '':
            x_content.append(node.attrib['content-desc'].lower().strip())

    y_id = []
    y_text = []
    y_content = []

    for node in y_screen.nodes:
        if node.attrib['resource-id'] != '':
            if '_' not in node.attrib['resource-id'] and '/' in node.attrib['resource-id']:
                y_id.append(node.attrib['resource-id'].split('/')[1])
            elif '_' in node.attrib['resource-id'] and '/' in node.attrib['resource-id']:
                tmp_list = node.attrib['resource-id'].split('/')[1].split('_')
                y_id.extend(tmp_list)
            else:
                y_id.append(node.attrib['resource-id'])

        if node.attrib['text'] != '':
            y_text.append(node.attrib['text'].lower().strip())

        if node.attrib['content-desc'] != '':
            y_content.append(node.attrib['content-desc'].lower().strip())

    # 计算id的相似度
    x_id_words = split_str(x_id)
    tmp_str = ' '
    x_id_str = tmp_str.join(x_id_words)
    # 获取tfidf处理过的词汇
    xx_id_words, x_weight = get_words_vector_by_tfidf([x_id_str])

    y_id_words = split_str(y_id)
    tmp_str = ' '
    y_id_str = tmp_str.join(y_id_words)
    # 获取tfidf处理过的词汇
    yy_id_words, y_weight = get_words_vector_by_tfidf([y_id_str])
    id_sim = get_words_sim(xx_id_words, x_weight, yy_id_words, y_weight)

    # print(y_words)

    # 计算text的相似度
    x_text_words = split_str(x_text)
    tmp_str = ' '
    x_text_str = tmp_str.join(x_text_words)
    # 获取tfidf处理过的词汇
    xx_text_words, x_weight = get_words_vector_by_tfidf([x_text_str])

    # print(x_words)

    y_text_words = split_str(y_text)
    tmp_str = ' '
    y_text_str = tmp_str.join(y_text_words)
    # 获取tfidf处理过的词汇
    yy_text_words, y_weight = get_words_vector_by_tfidf([y_text_str])
    text_sim = get_words_sim(xx_text_words, x_weight, yy_text_words, y_weight)

    # print(y_words)

    # 计算content的相似度
    x_content_words = split_str(x_content)
    tmp_str = ' '
    x_content_str = tmp_str.join(x_content_words)
    # 获取tfidf处理过的词汇
    xx_content_words, x_weight = get_words_vector_by_tfidf([x_content_str])

    # print(x_words)

    y_content_words = split_str(y_content)
    tmp_str = ' '
    y_content_str = tmp_str.join(y_content_words)
    # 获取tfidf处理过的词汇
    yy_content_words, y_weight = get_words_vector_by_tfidf([y_content_str])
    content_sim = get_words_sim(xx_content_words, x_weight, yy_content_words, y_weight)

    # print(y_words)

    id_flag = True
    text_flag = True
    content_flag = True

    if xx_id_words[0] == 'none' and yy_id_words[0] == 'none':
        id_flag = False

    if xx_text_words[0] == 'none' and yy_text_words[0] == 'none':
        text_flag = False

    if xx_content_words[0] == 'none' and yy_content_words[0] == 'none':
        content_flag = False

    sim_list = []

    if id_flag:
        sim_list.append(id_sim)

    if text_flag:
        sim_list.append(text_sim)

    if content_flag:
        sim_list.append(content_sim)

    final_sim = 0

    # 要求各方面的相似值不能相差太大了
    # sim_flag = True
    count = 0
    for score in sim_list:
        final_sim += score
        if score < 0.1:
            # sim_flag = False
            count += 1

    if count / len(sim_list) < 0.5:
        return final_sim / len(sim_list)
    else:
        return 0


def get_screen_sim2(x_screen, y_screen):
    """
    使用节点的xpath来判别 效果很差 基本上没用
    :param x_screen:
    :param y_screen:
    :return:
    """

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

    return count / max(len(x_xpath_list), len(y_xpath_list))


def get_elem_distance(x_node, y_node):
    """
    获得节点间的距离
    其实就是进行匹配
    :param x_node:
    :param y_node:
    :return:
    """

    dist = get_levenshtein_distance(x_node, y_node) + get_GUI_distance(x_node, y_node)

    return dist


def get_levenshtein_distance(x_node, y_node):
    """
    计算文本间的编辑距离
    :param str_x:
    :param str_y:
    :return:
    """
    return Levenshtein.distance(x_node.xpath[0], y_node.xpath[0])


def get_GUI_distance(x_node, y_node):
    """
    获取节点之间的gui距离
    :param x_node:
    :param y_node:
    :return:
    """
    return (abs(x_node.width - y_node.width) +
            abs(x_node.height - y_node.height) +
            abs(x_node.loc_x - y_node.loc_y) +
            abs(x_node.loc_x - y_node.loc_y))


def is_sim(x_node, y_node):
    """
    判断两个节点最终是否符合匹配的要求
    :param x_node:
    :param y_node:
    :return:
    """

    flag = True
    if get_levenshtein_distance(x_node, y_node) / max(len(x_node.xpath[0]), len(y_node.xpath[0])) > 0.5:
        flag = False

    if abs(x_node.width - y_node.width) / x_node.width > 0.3:
        flag = False

    if abs(x_node.height - y_node.height) / x_node.height > 0.3:
        flag = False

    if abs(x_node.loc_x - y_node.loc_x) / x_node.width > 1:
        flag = False

    if abs(x_node.loc_y - y_node.loc_y) / x_node.height > 1:
        flag = False

    return flag


def is_xpath_matched(x_node, y_node):
    """
    判断两个节点是否可以根据xpath匹配上
    """

    for x_xpath in x_node.xpath:
        if x_xpath in y_node.xpath:
            return True

    return False


# def is_str_matched(x_node, y_node):
#     """
#     判断两个节点的文本属性是否可以匹配上
#     因为有的时候 id text content-desc 并不总是相等的 可能会有微小的改变
#     :param x_node:
#     :param y_node:
#     :return:
#     """
#
#     if x_node.attrib['resource-id'] != '' or y_node.attrib['resource-id'] != '':
#         x_id = x_node.attrib['resource-id']
#         y_id = y_node.attrib['resource-id']
#         if x_node.attrib['resource-id'] != '':
#             x_id = x_id.split('/')[1]
#
#         if y_node.attrib['resource-id'] != '':
#             y_id = y_id.split('/')[1]
#
#         id_sim = 1 - Levenshtein.distance(x_id, y_id) / max(len(x_id), len(y_id))
#         if id_sim >= 0.5:
#             return True
#
#     if x_node.attrib['text'] != '' or y_node.attrib['text'] != '':
#         x_text = x_node.attrib['text']
#         y_text = y_node.attrib['text']
#         text_sim = 1 - Levenshtein.distance(x_text, y_text) / max(len(x_text), len(y_text))
#         if text_sim >= 0.5:
#             return True
#
#     if x_node.attrib['content-desc'] != '' or y_node.attrib['content-desc'] != '':
#         x_content = x_node.attrib['content-desc']
#         y_content = y_node.attrib['content-desc']
#         content_sim = 1 - Levenshtein.distance(x_content, y_content) / max(len(x_content), len(y_content))
#         if content_sim >= 0.5:
#             return True
#
#     return False


def get_str_sim(x_node, y_node):
    """
    获取两个节点间的字符文本相似度
    :param x_node:
    :param y_node:
    :return:
    """

    id_flag = False
    text_flag = False
    content_flag = False

    if x_node.attrib['resource-id'] != '' or y_node.attrib['resource-id'] != '':
        x_id = x_node.attrib['resource-id']
        y_id = y_node.attrib['resource-id']
        if x_node.attrib['resource-id'] != '':
            x_id = x_id.split('/')[1]

        if y_node.attrib['resource-id'] != '':
            y_id = y_id.split('/')[1]

        id_flag = True

        id_sim = 1 - Levenshtein.distance(x_id, y_id) / max(len(x_id), len(y_id))

    if x_node.attrib['text'] != '' or y_node.attrib['text'] != '':
        x_text = x_node.attrib['text']
        y_text = y_node.attrib['text']

        text_flag = True

        text_sim = 1 - Levenshtein.distance(x_text, y_text) / max(len(x_text), len(y_text))

    if x_node.attrib['content-desc'] != '' or y_node.attrib['content-desc'] != '':
        x_content = x_node.attrib['content-desc']
        y_content = y_node.attrib['content-desc']

        content_flag = True
        content_sim = 1 - Levenshtein.distance(x_content, y_content) / max(len(x_content), len(y_content))

    sim_list = []

    if id_flag:
        sim_list.append(id_sim)

    if text_flag:
        sim_list.append(text_sim)

    if content_flag:
        sim_list.append(content_sim)

    final_sim = 0

    for sim in sim_list:
        final_sim += sim

    if sim_list:
        return final_sim / len(sim_list)
    else:
        return final_sim

# def test():
#     a = 'SimCard'
#     b = 'SimCard(0)'
#     c = 'Phone'
#     d = ' Phone(0)'
#     print(1 - Levenshtein.distance(c, d) / max(len(c), len(d)))
#
#
# test()
