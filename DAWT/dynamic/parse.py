#!/u(sr/bin/python
import json

rendering = "Rendering"
painting = "Painting"
dependencies = "Deps"
images_ext = ["png","webp","jpeg","gif","jpg"]
js_ext = ["js","json"]

def parse(filename):
    '''
    { html_1 : {
        ID: html_1,
        parent: null,
        trigger: 0,
        completed: 1.12,
        children: [ (img_1, start_time), (img_2,start_time), ...]
    } 
    ...}
    '''

    with open(filename) as f:
        wprof_dict = json.load(f)
    
    result = {}
    for each_obj in wprof_dict:
        if 'id' in each_obj.keys() and each_obj['id'] not in [rendering,painting,dependencies]:
            for each_obj_id in each_obj['objs']:
                result[each_obj_id['activityId']] = {}
                result[each_obj_id['activityId']]["ID"] = each_obj_id['activityId']
                result[each_obj_id['activityId']]["parent"] = "null"
                result[each_obj_id['activityId']]["trigger"] = each_obj_id['startTime']
                result[each_obj_id['activityId']]["completed"] = each_obj_id['endTime']
                result[each_obj_id['activityId']]["children"] = []
                if "Networking" in each_obj_id['activityId']:
                    result[each_obj_id['activityId']]["mimeType"] = each_obj_id['mimeType']

    for each_obj in wprof_dict:
        if 'id' in each_obj.keys() and each_obj['id'] == dependencies:
            for each_dep in each_obj['objs']:
                result[each_dep['a1']]['children'].append(*list(zip([each_dep['a2']],[result[each_dep['a2']]['trigger']])))
                result[each_dep['a2']]['parent'] = each_dep['a1']
    
    return result

def main():
    filename = "wprof.json"
    res = parse(filename) 
    with open("output.json","w") as f:
        f.write(json.dumps(res))
    print("See output.json for result")


if __name__ == "__main__":
    main()
    

