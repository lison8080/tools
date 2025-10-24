# -*- coding: utf-8 -*-
"""使用 Faker 生成信用卡信息"""

from faker import Faker
import random

def generate_credit_card(count=1, locale='zh_CN', prefix=None, card_length=15):
    """
    生成信用卡信息
    
    Args:
        count: 生成的信用卡数量，默认为1
        locale: 地区设置，默认为中文
        prefix: 自定义卡号前缀，如 "3792403017"
        card_length: 卡号总长度，默认为15位
    """
    fake = Faker(locale)
    
    cards = []
    for i in range(count):
        # 生成卡号
        if prefix:
            # 使用自定义前缀
            remaining_length = card_length - len(prefix)
            random_digits = ''.join([str(random.randint(0, 9)) for _ in range(remaining_length)])
            card_number = prefix + random_digits
        else:
            # 使用 Faker 默认生成
            card_number = fake.credit_card_number()
        
        card = {
            '卡号': card_number,
            '持卡人': fake.name(),
            '卡类型': fake.credit_card_provider(),
            '过期日期': fake.credit_card_expire(),
            'CVV': fake.credit_card_security_code()
        }
        cards.append(card)
    
    return cards

def print_cards(cards):
    """格式化输出信用卡信息"""
    for idx, card in enumerate(cards, 1):
        print(f"\n{'='*50}")
        print(f"信用卡 #{idx}")
        print(f"{'='*50}")
        for key, value in card.items():
            print(f"{key:8}: {value}")

if __name__ == '__main__':
    # 生成5张信用卡，使用自定义前缀 3792403017
    cards = generate_credit_card(count=500, prefix='37924030', card_length=15)
    print_cards(cards)
    
    print(f"\n{'='*50}")
    print(f"共生成 {len(cards)} 张信用卡")
    print(f"{'='*50}")

