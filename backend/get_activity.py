from xml.dom.minidom import parse

# 使用minidom解析器打开 xml 文档
DOMTree = parse("AndroidManifest.txt")
collection = DOMTree.documentElement
act_list = collection.getElementsByTagName('activity')


act_name_list = []

for act in act_list:

    items = act.attributes.items()
    for tag in items:
        if 'android:name' in tag:
            print(tag[1])
            act_name_list.append(tag[1])

    print('---------')


print(len(act_name_list))



