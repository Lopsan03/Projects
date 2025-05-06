import re
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


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

    # Set each filter if it exists
    for field_id, value in filters.items():
        if value:
            Select(driver.find_element(By.ID, field_id)).select_by_value(value)

    # Set 'Solo Avisos con Fotografía'
    if kwargs.get('solo_foto'):
        checkbox_foto = driver.find_element(By.ID, 'ChbFoto')
        if not checkbox_foto.is_selected():
            checkbox_foto.click()

    # Click the search button
    driver.find_element(By.CSS_SELECTOR, '.btnSearch a').click()


# Function to extract links from all paginated search result pages
def extract_house_links(driver, base_url):
    house_links = []
    pagination_element = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_divcpx2")
    total_pages = len(pagination_element.find_elements(By.CLASS_NAME, "cpa")) + 1

    for page_num in range(1, total_pages + 1):
        print(f"Processing page {page_num}...")
        driver.get(f"{base_url}&Pagina={page_num}")
        time.sleep(2)

        elements = driver.find_elements(By.CSS_SELECTOR, 'a.tituloresult')
        house_links.extend(elem.get_attribute('href') for elem in elements)

    return list(set(house_links))  # Ensure unique links


# Function to extract house details from individual house links
def extract_house_details(driver, house_link, timeout=3):
    print(f"Processing link: {house_link}")
    driver.get(house_link)

    house_details = {'URL': house_link}
    try:
        # Skip if it's a real estate company link
        if WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//td[@class='carac_td']/a[contains(@href, 'http')]"))
        ):
            print(f"Skipping link: Real estate company found")
            return None
    except TimeoutException:
        pass

    # Skip links containing keywords indicating a real estate company
    try:
        info_paragraph = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='infocompleta']"))
        ).text.strip()

        real_estate_keywords = ['RAICES', 'INMUEBLES', 'REAL ESTATE', 'ASESORA', 'ASESOR']
        if any(keyword in info_paragraph.upper() for keyword in real_estate_keywords):
            print(f"Skipping link: Real estate keywords found")
            return None

        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', info_paragraph)
        if any(not email.endswith(('@gmail.com', '@hotmail.com')) for email in emails):
            print(f"Skipping link: Non-gmail/hotmail email found")
            return None
    except TimeoutException:
        pass

    # Extract house data
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
def scrape_real_estate_data():
    driver = webdriver.Chrome()
    driver.get("https://www.avisosdeocasion.com/venta-casas.aspx?PlazaBusqueda=2&Plaza=2")

    set_filters(driver, inmueble="3", estado="2", zona="15", colonia="0", solo_foto=True)
    URL = driver.current_url

    house_links = extract_house_links(driver, URL)

    houses_data = []
    for link in house_links:
        house_details = extract_house_details(driver, link)
        if house_details:
            houses_data.append(house_details)

    driver.quit()

    return pd.DataFrame(houses_data)


# Save the DataFrame to Excel and display it
def save_data_to_excel(df, filename="real_estate_data.xlsx"):
    if not df.empty:
        df.to_excel(filename, index=False)
        print(f"Data saved to {filename}")
    else:
        print("No data found to save.")


# Run the scraper, save data, and display the DataFrame
df = scrape_real_estate_data()

# Display the DataFrame
print(df)

# Save the DataFrame to an Excel file
save_data_to_excel(df)
