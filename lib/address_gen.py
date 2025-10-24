# -*- coding: utf-8 -*-
"""生成具体到门牌号的中国地址和邮政编码"""

import random
import json
import os

# 全局变量存储邮编数据
POSTCODE_DATA = {}
VALID_POSTCODES = []

def load_postcode_data():
    """从address.json加载邮编数据并提取非零邮编"""
    global POSTCODE_DATA, VALID_POSTCODES
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'address.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            POSTCODE_DATA = json.load(f)
        
        # 提取所有不为"0"和不为"000000"的邮编
        VALID_POSTCODES = [
            (postcode, district) 
            for postcode, district in POSTCODE_DATA.items() 
            if postcode != "0" and postcode != "000000" and not postcode.startswith("00000")
        ]
        
        print(f"成功加载 {len(VALID_POSTCODES)} 个有效邮编")
        return True
    except Exception as e:
        print(f"加载邮编数据失败: {e}")
        return False

# 常用街道名称
COMMON_STREETS = [
    '人民路', '解放路', '中山路', '建设路', '和平路', '胜利路', 
    '光明路', '文化路', '新华路', '育才路', '民主路', '幸福路',
    '东风路', '西大街', '南门街', '北环路', '中心大道', '府前街',
    '工业路', '商业街', '学府路', '体育路', '公园路', '滨河路'
]

def generate_address(count=1):
    """
    生成中国地址和邮政编码（从address.json中读取真实邮编）
    
    Args:
        count: 生成的地址数量，默认为1
    
    Returns:
        包含地址信息的字典列表
    """
    # 确保已加载邮编数据
    if not VALID_POSTCODES:
        if not load_postcode_data():
            print("无法加载邮编数据，无法生成地址")
            return []
    
    # 常见建筑类型
    building_types = ['号', '号楼', '号院']
    
    addresses = []
    for i in range(count):
        # 从有效邮编中随机选择
        postcode, district_name = random.choice(VALID_POSTCODES)
        
        # 解析地区信息（尝试智能分割）
        # 邮编对应的区县名称
        district = district_name.strip()
        
        # 根据区县名猜测省市（简化处理）
        # 这里可以根据邮编前缀判断省份
        province, city = parse_province_city(postcode, district)
        
        # 随机选择街道
        street_name = random.choice(COMMON_STREETS)
        
        # 生成门牌号
        building_number = random.randint(1, 999)
        building_type = random.choice(building_types)
        
        # 可能添加单元和房号
        if random.random() > 0.5:
            unit = random.randint(1, 6)
            room = random.randint(101, 2999)
            detail = f"{building_number}{building_type}{unit}单元{room}室"
        else:
            detail = f"{building_number}{building_type}"
        
        # 组合完整地址
        full_address = f"{province}{city}{district}{street_name}{detail}"
        
        address_info = {
            '省份': province,
            '城市': city,
            '区县': district,
            '街道': street_name,
            '门牌号': detail,
            '完整地址': full_address,
            '邮政编码': postcode
        }
        addresses.append(address_info)
    
    return addresses

def parse_province_city(postcode, district):
    """根据邮编前缀推断省份和城市"""
    prefix = postcode[:2]
    
    # 邮编前两位到省份的映射
    province_map = {
        '10': ('北京市', '北京市'),
        '11': ('北京市', '北京市'),
        '12': ('天津市', '天津市'),
        '13': ('河北省', '石家庄市'),
        '14': ('山西省', '太原市'),
        '15': ('内蒙古自治区', '呼和浩特市'),
        '20': ('上海市', '上海市'),
        '21': ('辽宁省', '沈阳市'),
        '22': ('吉林省', '长春市'),
        '23': ('黑龙江省', '哈尔滨市'),
        '24': ('辽宁省', '沈阳市'),
        '25': ('吉林省', '长春市'),
        '26': ('黑龙江省', '哈尔滨市'),
        '30': ('上海市', '上海市'),
        '31': ('江苏省', '南京市'),
        '32': ('江苏省', '南京市'),
        '33': ('浙江省', '杭州市'),
        '34': ('安徽省', '合肥市'),
        '35': ('福建省', '福州市'),
        '36': ('江西省', '南昌市'),
        '37': ('山东省', '济南市'),
        '40': ('河南省', '郑州市'),
        '41': ('河南省', '郑州市'),
        '42': ('湖北省', '武汉市'),
        '43': ('湖南省', '长沙市'),
        '44': ('广东省', '广州市'),
        '45': ('广西壮族自治区', '南宁市'),
        '46': ('海南省', '海口市'),
        '50': ('重庆市', '重庆市'),
        '51': ('四川省', '成都市'),
        '52': ('贵州省', '贵阳市'),
        '53': ('云南省', '昆明市'),
        '54': ('西藏自治区', '拉萨市'),
        '61': ('陕西省', '西安市'),
        '62': ('甘肃省', '兰州市'),
        '63': ('青海省', '西宁市'),
        '64': ('宁夏回族自治区', '银川市'),
        '65': ('新疆维吾尔自治区', '乌鲁木齐市'),
        '71': ('台湾省', '台北市'),
        '81': ('香港特别行政区', '香港'),
        '82': ('澳门特别行政区', '澳门'),
    }
    
    # 获取省份和默认城市
    province, city = province_map.get(prefix, ('中国', '未知市'))
    
    # 尝试从区县名中提取市名
    if '市' in district and district != city:
        # 如果区县名包含市，可能是直辖市的区或者地级市
        city_match = district.split('市')[0] + '市'
        if len(city_match) < 10:  # 合理的市名长度
            city = city_match
    
    return province, city

def print_addresses(addresses):
    """格式化输出地址信息"""
    for idx, addr in enumerate(addresses, 1):
        print(f"\n{'='*50}")
        print(f"地址 #{idx}")
        print(f"{'='*50}")
        print(f"完整地址: {addr['完整地址']}")
        print(f"邮政编码: {addr['邮政编码']}")
        print(f"\n详细信息:")
        print(f"  省份: {addr['省份']}")
        print(f"  城市: {addr['城市']}")
        print(f"  区县: {addr['区县']}")
        print(f"  街道: {addr['街道']}")
        print(f"  门牌号: {addr['门牌号']}")

if __name__ == '__main__':
    print("正在加载邮编数据...")
    if load_postcode_data():
        print(f"数据加载成功！共 {len(VALID_POSTCODES)} 个有效邮编\n")
        
        # 生成10个地址
        addresses = generate_address(count=10)
        print_addresses(addresses)
        
        print(f"\n{'='*50}")
        print(f"共生成 {len(addresses)} 个地址")
        print(f"{'='*50}")
    else:
        print("加载邮编数据失败，请检查 address.json 文件是否存在")

