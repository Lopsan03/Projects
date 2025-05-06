import re
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os

# Helper function to convert publication date string to a datetime object
def convert_to_date(date_str):
    month_map = {
        'Ene': '01', 'Feb': '02', 'Mar': '03', 'Abr': '04', 'May': '05', 'Jun': '06',
        'Jul': '07', 'Ago': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dic': '12'
    }
    date_str = date_str.replace('Publicado el ', '')
    day, month = date_str.split(' de ')
    date_str = f"{datetime.now().year}-{month_map[month]}-{int(day):02d}"
    return datetime.strptime(date_str, '%Y-%m-%d')

# Function to apply search filters on the webpage
def set_filters(driver, **kwargs):
    filters = {
        'idinmueble': kwargs.get('inmueble'),
        'Estado': kwargs.get('estado'),
        'Zonas': kwargs.get('zona'),
        'Colonia': kwargs.get('colonia'),
        'PrecioInicial': kwargs.get('precio_inicial'),
        'PrecioFinal': kwargs.get('precio_final'),
        'TerrenoInicial': kwargs.get('m2_terreno_inicial'),
        'TerrenoFinal': kwargs.get('m2_terreno_final'),
        'ConstruccionInicial': kwargs.get('m2_construccion_inicial'),
        'ConstruccionFinal': kwargs.get('m2_construccion_final'),
        'Plantas': kwargs.get('plantas'),
        'Banios': kwargs.get('banios'),
        'Recamaras': kwargs.get('recamaras')
    }

    for field_id, value in filters.items():
        if value:
            Select(driver.find_element(By.ID, field_id)).select_by_value(value)

    if kwargs.get('solo_foto'):
        checkbox_foto = driver.find_element(By.ID, 'ChbFoto')
        if not checkbox_foto.is_selected():
            checkbox_foto.click()

    driver.find_element(By.CSS_SELECTOR, '.btnSearch a').click()

# Function to extract links from all paginated search result pages
def extract_house_links(driver, base_url):
    house_links = []
    pagination_element = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_divcpx2")
    total_pages = len(pagination_element.find_elements(By.CLASS_NAME, "cpa")) + 1

    for page_num in range(1, total_pages + 1):
        driver.get(f"{base_url}&Pagina={page_num}")
        time.sleep(2)

        elements = driver.find_elements(By.CSS_SELECTOR, 'a.tituloresult')
        house_links.extend(elem.get_attribute('href') for elem in elements)

    return list(set(house_links))  # Ensure unique links

# Function to extract house details from individual house links
def extract_house_details(driver, house_link, timeout=3):
    driver.get(house_link)

    house_details = {'URL': house_link}
    try:
        if WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//td[@class='carac_td']/a[contains(@href, 'http')]"))
        ):
            return None
    except TimeoutException:
        pass

    try:
        info_paragraph = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='infocompleta']"))
        ).text.strip()

        real_estate_keywords = ['RAICES', 'INMUEBLES', 'REAL ESTATE', 'ASESORA', 'ASESOR']
        if any(keyword in info_paragraph.upper() for keyword in real_estate_keywords):
            return None

        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', info_paragraph)
        if any(not email.endswith(('@gmail.com', '@hotmail.com')) for email in emails):
            return None
    except TimeoutException:
        pass

    xpaths = {
        'Zone': "//td[@style='width:65%;']/h2[contains(text(), 'ZONA')]/b",
        'Colony': "//td/h2[contains(text(), 'COLONIA')]/span/b",
        'Price': "//td[@align='right']/h2/b",
        'Publication Date': "//td[@class='carac_td' and contains(text(), 'Publicado')]",
        'Bedrooms': "//td[@class='carac_td']/h3[contains(text(), 'Recámaras')]",
        'Bathrooms': "//td[@class='carac_td']/h3[contains(text(), 'Baños')]",
        'Construction Size': "//td[@class='carac_td']/h3[contains(text(), 'Construcción')]",
        'Land Size': "//td[@class='carac_td']/h3[contains(text(), 'Terreno')]",
        'Floors': "//td[@class='carac_td']/h3[contains(text(), 'Planta')]",
    }

    for key, xpath in xpaths.items():
        try:
            element_text = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            ).text.strip()

            if key in ['Bedrooms', 'Bathrooms', 'Construction Size', 'Land Size', 'Floors']:
                element_text = int(re.sub(r'[^\d]', '', element_text))
            if key == 'Price':
                element_text = int(re.sub(r'[^\d]', '', element_text))
            if key == 'Publication Date':
                element_text = convert_to_date(element_text)

            house_details[key] = element_text
        except TimeoutException:
            house_details[key] = None

    return house_details

# Main scraping function
def scrape_real_estate_data(zonas):
    driver = webdriver.Chrome()
    driver.get("https://www.avisosdeocasion.com/venta-casas.aspx?PlazaBusqueda=2&Plaza=2")

    all_houses_data = []
    for zona in zonas:
        set_filters(driver, inmueble="3", estado="2", zona=str(zona), colonia="0", solo_foto=True)
        URL = driver.current_url

        house_links = extract_house_links(driver, URL)

        for link in house_links:
            house_details = extract_house_details(driver, link)
            if house_details:
                all_houses_data.append(house_details)

    driver.quit()

    return pd.DataFrame(all_houses_data)

# Check for new properties and update Excel
def update_excel_with_new_data(df, filename="real_estate_data.xlsx"):
    if os.path.exists(filename):
        existing_df = pd.read_excel(filename)
        new_properties = df[~df['URL'].isin(existing_df['URL'])]

        if not new_properties.empty:
            updated_df = pd.concat([existing_df, new_properties], ignore_index=True)
            updated_df.to_excel(filename, index=False)
            print(f"{len(new_properties)} new properties found and added to {filename}")
        else:
            print("No new properties found.")
    else:
        df.to_excel(filename, index=False)
        print(f"Excel file created with {len(df)} properties.")

# Run the scraper every hour and check for new properties
def run_hourly_scraper():
    zonas = [15, 16]
    while True:
        df = scrape_real_estate_data(zonas)
        if not df.empty:
            update_excel_with_new_data(df)
        else:
            print("No properties found in this run.")
        time.sleep(3600)  # Wait for 1 hour before running again

# Start the process
run_hourly_scraper()
