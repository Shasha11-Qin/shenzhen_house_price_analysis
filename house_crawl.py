# coding:utf-8
"""
项目来源于和鲸社区，原作者: - K. -
功能：
✅ 自动循环爬取深圳各区二手房
✅ 自动翻页，解析标题、面积、楼层、价格、地铁、学区、小区等信息
✅ 输出单区 Excel + 汇总文件
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import re, os, time, random

# ===== 初始化浏览器 =====
chrome_path = r"D:\Apps\chromedriver.exe"
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-infobars")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=Service(chrome_path), options=options)
wait = WebDriverWait(driver, 15)

base_url = 'https://sz.esf.fang.com/'
driver.get(base_url)
print("✅ 已打开搜房深圳站首页")

# ===== 区域 xpath 映射表 =====
list_xpath = [
    ['longgang','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[1]/a'],
    ['longhua','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[2]/a'],
    ['baoan','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[3]/a'],
    ['nanshan','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[4]/a'],
    ['futian','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[5]/a'],
    ['luohu','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[6]/a'],
    ['pingshan','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[7]/a'],
    ['guangming','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[8]/a'],
    ['yantian','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[9]/a'],
    ['dapengxinqu','//*[@id="kesfqbfylb_A01_03_01"]/ul/li[10]/a']
]

# ===== 输出目录 =====
output_dir = r"E:\Data_Sets_of_Analysis\Project_2_House_Price_of_ShenZhen\Data_2025"
os.makedirs(output_dir, exist_ok=True)

df_all = pd.DataFrame()
# ====== 新增：学区房判断函数 ======
def is_school_house(title, label_info, tel_shop, add_shop):
    school_keywords = [
        '学位', '学区', '学校', '名校', '重点小学', '重点中学',
        '实验学校', '一贯制', '九年一贯制', '省一级', '教育局',
        '学位未用', '学位未占用','优质教育'
    ]

    text = f"{title} {label_info} {tel_shop} {add_shop}"

    return 1 if any(k in text for k in school_keywords) else 0


# ===== 主循环：按区爬取 =====
for xpath in list_xpath:
    district_name = xpath[0]
    print(f"\n========== 🏙 开始爬取 {district_name} ==========")

    driver.get(base_url)
    try:
        elem = wait.until(EC.element_to_be_clickable((By.XPATH, xpath[1])))
        driver.execute_script("arguments[0].click();", elem)
        print(f"✅ 进入 {district_name} 区页面")
    except Exception as e:
        print(f"⚠️ 无法点击 {district_name}：{e}")
        continue

    df = pd.DataFrame()
    page = 1

    while True:
        print(f"⏳ 正在爬取第 {page} 页...")
        try:
            wait.until(EC.presence_of_all_elements_located((By.XPATH, '//dl[@dataflag="bg"]')))
            time.sleep(random.uniform(2, 4))
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.5, 3.5))
            houses = driver.find_elements(By.XPATH, '//dl[@dataflag="bg"]')
        except:
            print("⚠️ 页面加载失败，跳过该页")
            break

        for h in houses:
            try:
                title = h.find_element(By.XPATH, './/h4/a/span').text.strip()
                tel_shop = h.find_element(By.XPATH, './/p[@class="tel_shop"]').text.strip()
                add_shop = h.find_element(By.XPATH, './/p[@class="add_shop"]').text.strip()
                try:
                    label_info = h.find_element(By.XPATH, './/p[contains(@class,"label")]').text.strip()
                except:
                    label_info = ""

                total_price = h.find_element(By.XPATH, './/dd[@class="price_right"]//b').text.strip()
                unit_price_text = h.find_element(By.XPATH, './/dd[@class="price_right"]/span[last()]').text.strip()
                unit_price = re.findall(r'(\d+)', unit_price_text)
                unit_price = float(unit_price[0]) if unit_price else None

                # ==== 正则提取字段 ====
                roomnum = re.findall(r'(\d)室', tel_shop)
                hall = re.findall(r'(\d)厅', tel_shop)
                area = re.findall(r'(\d+\.?\d*)㎡', tel_shop)
                floor = re.findall(r'(高层|中层|低层)', tel_shop)

                # ==== Subway 判断 ====
                subway = 1 if ('地铁' in label_info or '距' in label_info) else 0

                # ==== 学区房增强判断 ====
                school = is_school_house(title, label_info, tel_shop, add_shop)

                df = pd.concat([df, pd.DataFrame([{
                    'district': district_name,
                    'title': title,
                    'roomnum': int(roomnum[0]) if roomnum else None,
                    'hall': int(hall[0]) if hall else None,
                    'AREA': float(area[0]) if area else None,
                    'C_floor': floor[0].replace('高层', 'high').replace('中层', 'middle').replace('低层',
                                                                                                  'low') if floor else None,
                    'school': school,
                    'subway': subway,
                    'per_price(元/㎡)': unit_price,
                    'total_price(万)': float(total_price),
                    'address': add_shop,
                    'label': label_info
                }])])

            except Exception as e:
                print("⚠️ 跳过异常房源:", e)
                continue

        # ===== 翻页逻辑 =====
        try:
            next_btn = driver.find_element(By.LINK_TEXT, "下一页")
            if "no" in next_btn.get_attribute("class"):
                print("🚫 已到最后一页")
                break
            driver.execute_script("arguments[0].click();", next_btn)
            page += 1
            time.sleep(random.uniform(3, 6))
        except:
            print("⚠️ 未找到下一页按钮，结束该区")
            break

    # ===== 保存单区文件 =====
    if not df.empty:
        save_path = os.path.join(output_dir, f"sz_{district_name}_2025.xlsx")
        df.to_excel(save_path, index=False)
        print(f"✅ 已保存 {district_name} 区数据，共 {df.shape[0]} 条 → {save_path}")
        df_all = pd.concat([df_all, df])
    else:
        print(f"⚠️ {district_name} 区无有效数据")

# ===== 汇总输出 =====
summary_path = os.path.join(output_dir, "深圳二手房_2025汇总.xlsx")
df_all.to_excel(summary_path, index=False)
print("\n==============================")
print(f"🎉 全部爬取完成，共 {df_all.shape[0]} 条数据")
print(f"📂 汇总文件：{summary_path}")
print("==============================")

driver.quit()
