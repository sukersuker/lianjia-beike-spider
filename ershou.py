#!/usr/bin/env python
# coding=utf-8
# author: Zeng YueTian
# 此代码仅供学习与交流，请勿用于商业用途。
# 获得指定城市的二手房数据

import threadpool
import threading
from lib.utility.date import *
from lib.zone.area import *
from lib.utility.path import *
from lib.spider.xiaoqu import *
from lib.item.ershou import *
from lib.spider.spider import *
from lib.spider.spider import thread_pool_size


def collect_area_ershou_data(city_name, area_name, fmt="csv"):
    """
    对于每个板块,获得这个板块下所有二手房的信息
    并且将这些信息写入文件保存
    :param city_name: 城市
    :param area_name: 板块
    :param fmt: 保存文件格式
    :return: None
    """
    global total_num, today_path

    csv_file = today_path + "/{0}.csv".format(area_name)
    with open(csv_file, "w") as f:
        # 开始获得需要的板块数据
        ershous = get_area_ershou_info(city_name, area_name)
        # 锁定，多线程读写
        if mutex.acquire(1):
            total_num += len(ershous)
            # 释放
            mutex.release()
        if fmt == "csv":
            for ershou in ershous:
                # print(date_string + "," + xiaoqu.text())
                f.write(date_string + "," + ershou.text()+"\n")
    print("Finish crawl area: " + area_name + ", save data to : " + csv_file)


def get_area_ershou_info(city_name, area_name):
    """
    通过爬取页面获得城市指定版块的二手房信息
    :param city_name: 城市
    :param area_name: 版块
    :return: 二手房数据列表
    """
    district_name = area_dict.get(area_name, "")
    # 中文区县
    chinese_district = get_chinese_district(district_name)
    # 中文版块
    chinese_area = chinese_area_dict.get(area_name, "")

    ershou_list = list()
    page = 'http://{0}.{1}.com/ershoufang/{2}/'.format(city_name, SPIDER_NAME, area_name)
    print(page)  # 打印版块页面地址
    headers = create_headers()
    response = requests.get(page, timeout=10, headers=headers)
    html = response.content
    soup = BeautifulSoup(html, "lxml")

    # 获得总的页数，通过查找总页码的元素信息
    try:
        page_box = soup.find_all('div', class_='page-box')[0]
        matches = re.search('.*"totalPage":(\d+),.*', str(page_box))
        total_page = int(matches.group(1))
    except Exception as e:
        print("\tWarning: only find one page for {0}".format(area_name))
        print("\t" + e.message)
        total_page = 1

    # 从第一页开始,一直遍历到最后一页
    for num in range(1, total_page + 1):
        page = 'http://{0}.{1}.com/ershoufang/{2}/pg{3}'.format(city_name, SPIDER_NAME, area_name, num)
        print(page)     # 打印每一页的地址
        headers = create_headers()
        response = requests.get(page, timeout=10, headers=headers)
        html = response.content
        soup = BeautifulSoup(html, "lxml")

        # 获得有小区信息的panel
        house_elements = soup.find_all('li', class_="clear")
        for house_elem in house_elements:
            price = house_elem.find('div', class_="totalPrice")
            name = house_elem.find('div', class_='title')
            desc = house_elem.find('div', class_="houseInfo")

            # 继续清理数据
            price = price.text.strip()
            name = name.text.replace("\n", "")
            desc = desc.text.replace("\n", "").strip()

            # 作为对象保存
            ershou = ErShou(chinese_district, chinese_area, name, price, desc)
            ershou_list.append(ershou)
    return ershou_list


# -------------------------------
# main函数从这里开始
# -------------------------------
if __name__ == "__main__":
    spider = Spider(SPIDER_NAME)
    city = spider.get_city()

    # 准备日期信息，爬到的数据存放到日期相关文件夹下
    date_string = get_date_string()
    print('Today date is: %s' % date_string)
    today_path = create_date_path("{0}/ershou".format(SPIDER_NAME), city, date_string)

    mutex = threading.Lock()    # 创建锁
    total_num = 0               # 总的小区个数，用于统计
    t1 = time.time()            # 开始计时

    # 获得城市有多少区列表, district: 区县
    districts = get_districts(city)
    print('City: {0}'.format(city))
    print('Districts: {0}'.format(districts))

    # 获得每个区的板块, area: 板块
    areas = list()
    for district in districts:
        areas_of_district = get_areas(city, district)
        print('{0}: Area list:  {1}'.format(district, areas_of_district))
        # 用list的extend方法,L1.extend(L2)，该方法将参数L2的全部元素添加到L1的尾部
        areas.extend(areas_of_district)
        # 使用一个字典来存储区县和板块的对应关系, 例如{'beicai': 'pudongxinqu', }
        for area in areas_of_district:
            area_dict[area] = district
    print("Area:", areas)
    print("District and areas:", area_dict)

    # 准备线程池用到的参数
    nones = [None for i in range(len(areas))]
    city_list = [city for i in range(len(areas))]
    args = zip(zip(city_list, areas), nones)
    # areas = areas[0: 1]   # For debugging

    # 针对每个板块写一个文件,启动一个线程来操作
    pool_size = thread_pool_size
    pool = threadpool.ThreadPool(pool_size)
    my_requests = threadpool.makeRequests(collect_area_ershou_data, args)
    [pool.putRequest(req) for req in my_requests]
    pool.wait()
    pool.dismissWorkers(pool_size, do_join=True)        # 完成后退出

    # 计时结束，统计结果
    t2 = time.time()
    print("Total crawl {0} areas.".format(len(areas)))
    print("Total cost {0} second to crawl {1} data items.".format(t2 - t1, total_num))
