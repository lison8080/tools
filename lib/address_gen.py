# -*- coding: utf-8 -*-
"""生成具体到门牌号的中国地址和邮政编码"""

import random

# 真实的中国地址和邮政编码数据
REAL_ADDRESSES = [
    # 北京市
    {'province': '北京市', 'city': '北京市', 'district': '东城区', 'streets': ['长安街', '王府井大街', '东单北大街', '建国门内大街'], 'postcode': '100010'},
    {'province': '北京市', 'city': '北京市', 'district': '西城区', 'streets': ['西单北大街', '复兴门内大街', '金融街', '阜成门内大街'], 'postcode': '100032'},
    {'province': '北京市', 'city': '北京市', 'district': '朝阳区', 'streets': ['建国路', '朝阳路', '三里屯路', '望京街'], 'postcode': '100020'},
    {'province': '北京市', 'city': '北京市', 'district': '海淀区', 'streets': ['中关村大街', '学院路', '清华东路', '北四环西路'], 'postcode': '100080'},
    
    # 上海市
    {'province': '上海市', 'city': '上海市', 'district': '黄浦区', 'streets': ['南京东路', '淮海中路', '人民大道', '西藏中路'], 'postcode': '200001'},
    {'province': '上海市', 'city': '上海市', 'district': '徐汇区', 'streets': ['衡山路', '肇嘉浜路', '天钥桥路', '漕溪北路'], 'postcode': '200030'},
    {'province': '上海市', 'city': '上海市', 'district': '浦东新区', 'streets': ['世纪大道', '浦东南路', '张杨路', '陆家嘴环路'], 'postcode': '200120'},
    {'province': '上海市', 'city': '上海市', 'district': '杨浦区', 'streets': ['五角场', '国定路', '四平路', '大学路'], 'postcode': '200433'},
    
    # 广东省广州市
    {'province': '广东省', 'city': '广州市', 'district': '天河区', 'streets': ['天河路', '体育东路', '林和西路', '珠江新城'], 'postcode': '510630'},
    {'province': '广东省', 'city': '广州市', 'district': '越秀区', 'streets': ['中山路', '北京路', '解放路', '东风路'], 'postcode': '510030'},
    {'province': '广东省', 'city': '广州市', 'district': '海珠区', 'streets': ['江南大道', '新港路', '滨江路', '工业大道'], 'postcode': '510220'},
    
    # 广东省深圳市
    {'province': '广东省', 'city': '深圳市', 'district': '福田区', 'streets': ['深南大道', '福华路', '益田路', '彩田路'], 'postcode': '518033'},
    {'province': '广东省', 'city': '深圳市', 'district': '南山区', 'streets': ['深南大道', '科技园', '后海大道', '南海大道'], 'postcode': '518052'},
    {'province': '广东省', 'city': '深圳市', 'district': '罗湖区', 'streets': ['人民南路', '建设路', '东门路', '宝安南路'], 'postcode': '518001'},
    
    # 浙江省杭州市
    {'province': '浙江省', 'city': '杭州市', 'district': '西湖区', 'streets': ['文二路', '教工路', '天目山路', '西溪路'], 'postcode': '310012'},
    {'province': '浙江省', 'city': '杭州市', 'district': '上城区', 'streets': ['延安路', '解放路', '庆春路', '建国路'], 'postcode': '310002'},
    {'province': '浙江省', 'city': '杭州市', 'district': '滨江区', 'streets': ['滨盛路', '江南大道', '西兴路', '长河路'], 'postcode': '310051'},
    
    # 江苏省南京市
    {'province': '江苏省', 'city': '南京市', 'district': '鼓楼区', 'streets': ['中山路', '中央路', '汉中路', '湖南路'], 'postcode': '210008'},
    {'province': '江苏省', 'city': '南京市', 'district': '玄武区', 'streets': ['中山东路', '珠江路', '北京东路', '龙蟠路'], 'postcode': '210018'},
    
    # 四川省成都市
    {'province': '四川省', 'city': '成都市', 'district': '武侯区', 'streets': ['人民南路', '科华路', '红牌楼', '桐梓林路'], 'postcode': '610041'},
    {'province': '四川省', 'city': '成都市', 'district': '锦江区', 'streets': ['红星路', '春熙路', '东大街', '盐市口'], 'postcode': '610021'},
    {'province': '四川省', 'city': '成都市', 'district': '高新区', 'streets': ['天府大道', '剑南大道', '益州大道', '世纪城路'], 'postcode': '610041'},
    
    # 湖北省武汉市
    {'province': '湖北省', 'city': '武汉市', 'district': '武昌区', 'streets': ['中南路', '武珞路', '解放路', '中北路'], 'postcode': '430071'},
    {'province': '湖北省', 'city': '武汉市', 'district': '江汉区', 'streets': ['解放大道', '建设大道', '中山大道', '新华路'], 'postcode': '430023'},
    
    # 陕西省西安市
    {'province': '陕西省', 'city': '西安市', 'district': '雁塔区', 'streets': ['小寨路', '长安路', '电子路', '高新路'], 'postcode': '710061'},
    {'province': '陕西省', 'city': '西安市', 'district': '莲湖区', 'streets': ['北大街', '西大街', '莲湖路', '桃园路'], 'postcode': '710003'},
    
    # 天津市
    {'province': '天津市', 'city': '天津市', 'district': '和平区', 'streets': ['南京路', '和平路', '滨江道', '赤峰道'], 'postcode': '300041'},
    {'province': '天津市', 'city': '天津市', 'district': '河西区', 'streets': ['友谊路', '平山道', '围堤道', '大沽南路'], 'postcode': '300202'},
    
    # 重庆市
    {'province': '重庆市', 'city': '重庆市', 'district': '渝中区', 'streets': ['解放碑', '民权路', '邹容路', '八一路'], 'postcode': '400010'},
    {'province': '重庆市', 'city': '重庆市', 'district': '江北区', 'streets': ['观音桥', '建新东路', '红旗河沟', '北滨路'], 'postcode': '400020'},
]

def generate_address(count=1):
    """
    生成中国地址和邮政编码
    
    Args:
        count: 生成的地址数量，默认为1
    
    Returns:
        包含地址信息的字典列表
    """
    # 常见建筑类型
    building_types = ['号', '号楼', '号院']
    
    addresses = []
    for i in range(count):
        # 从真实地址数据中随机选择
        addr_data = random.choice(REAL_ADDRESSES)
        
        province = addr_data['province']
        city = addr_data['city']
        district = addr_data['district']
        street_name = random.choice(addr_data['streets'])
        postcode = addr_data['postcode']
        
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
    # 生成10个地址
    addresses = generate_address(count=10)
    print_addresses(addresses)
    
    print(f"\n{'='*50}")
    print(f"共生成 {len(addresses)} 个地址")
    print(f"{'='*50}")

