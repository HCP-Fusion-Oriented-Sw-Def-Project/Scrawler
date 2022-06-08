from compare.str_utility import split_str, get_words_vector_by_tfidf, get_words_sim
from compare.utility import is_xpath_matched, get_str_sim


def get_screen_sim_score(x_screen, y_screen, s_i, s_ii, t_j, t_k):
    """
    获取两个页面的相似度 使用id/text/content-desc
    还需要考虑到步长的cost
    :param x_screen:
    :param y_screen:

    s_i是source序列的上一个页面序号
    s_ii是当前需要映射的页面序号  对于s来说 步长为 s_ii - s_i
    t_j是上一个页面的序号
    t_k是当前页面的序号     对于t来说 步长为 t_k - t_j

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
            if '/' in node.attrib['resource-id']:
                if '_' not in node.attrib['resource-id']:
                    x_id.append(node.attrib['resource-id'].split('/')[1])
                else:
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
            if '/' in node.attrib['resource-id']:
                if '_' not in node.attrib['resource-id']:
                    y_id.append(node.attrib['resource-id'].split('/')[1])
                else:
                    tmp_list = node.attrib['resource-id'].split('/')[1].split('_')
                    y_id.extend(tmp_list)
            else:
                x_id.append(node.attrib['resource-id'])

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
        final_sim /= len(sim_list)
    else:
        final_sim = 0

    # 计算步长cost的公式 jumpCost = log2(|jump_t - jump_s| + 1) + 1

    # jump_t = t_k - t_j
    # jump_s = s_ii - s_i
    #
    # jump_cost = np.log2(abs(jump_t - jump_s) + 1) + 1
    #
    # return final_sim / jump_cost

    return final_sim


def get_edge_sim_score(source_screens, source_edges, screens, edges, x_screen, y_screen):
    """
    计算到达页面两条边的相似度
    :param source_edges:
    :param edges:
    :param x_screen:
    :param y_screen:
    :return:
    """

    b_edge = None
    u_edge = None

    # 首先获取以x_screen为des的边
    for edge in source_edges:
        if edge.end_id == x_screen.id:
            b_edge = edge
            break

    # 然后获取以y_screen为des的边
    for edge in edges:
        if edge.end_id == y_screen.id:
            u_edge = edge
            break

    b_begin_screen = None
    u_begin_screen = None

    # 然后获取b_edge的起点页面
    for screen in source_screens:
        if screen.id == b_edge.begin_id:
            b_begin_screen = screen
            break

    # 然后获取u_edge的起点页面
    for screen in screens:
        if screen.id == u_edge.begin_id:
            u_begin_screen = screen
            break

    # 获取边中点击的元素
    b_node = b_begin_screen.get_node_by_id(b_edge.node_id)
    u_node = u_begin_screen.get_node_by_id(u_edge.node_id)

    if is_xpath_matched(b_node, u_node):
        sim = 1

    else:
        sim = get_str_sim(b_node, u_node)

    return sim


def is_same_one(x_screen, y_screen):
    """
    判断是否是同一个页面
    因为有环的话 在场景模型中 这个页面会出现两次 最后的那个页面会无法匹配
    :param x_screen:
    :param y_screen:
    :return:
    """

    x_path = []
    y_xpath = []

    for node in x_screen.nodes:
        x_path.append(node.xpath[0])

    for node in y_screen.nodes:
        y_xpath.append(node.xpath[0])

    # print(x_path)
    # print(y_xpath)

    # count = 0
    # for xpath in x_path:
    #     for t_xpath in y_xpath:
    #         if x_path == t_xpath:
    #             count += 1

    # if count / max(len(x_path), len(y_xpath)) >= 0.95:
    #     return True

    return False
