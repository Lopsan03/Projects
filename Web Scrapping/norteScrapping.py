from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Initialize WebDriver (change the path to where your WebDriver is located)
driver = webdriver.Chrome(executable_path='/path/to/chromedriver')

# Open the website
driver.get('https://www.avisosdeocasion.com/')  # Replace with actual URL

# Wait until the page is fully loaded
wait = WebDriverWait(driver, 10)

# 1. Select "Venta" under "Transacción"
venta_option = wait.until(EC.element_to_be_clickable((By.ID, "Venta")))
venta_option.click()

# 2. Select "Casas" under "Inmueble"
inmueble_select = Select(wait.until(EC.element_to_be_clickable((By.ID, "FNivel2"))))
inmueble_select.select_by_value("120")  # Value for "Casas"

# 3. Select "Nuevo León" under "Estado"
estado_select = Select(wait.until(EC.element_to_be_clickable((By.ID, "FEstado"))))
estado_select.select_by_value("19")  # Value for "Nuevo León"

# 4. Select "Todas" under "Zona"
zona_select = Select(wait.until(EC.element_to_be_clickable((By.ID, "FZona"))))
zona_select.select_by_value("0")  # Value for "Todas"

# 5. Select all colonias (defaults to "Todas")
# No need to click anything as "Todas" is already selected by default

# 6. Select the "Sólo con foto" checkbox
solo_con_foto = driver.find_element(By.ID, "con-foto")
if not solo_con_foto.is_selected():
    solo_con_foto.click()

# 7. Click the "Mostrar" button to display results
mostrar_button = driver.find_element(By.XPATH, '//input[@value="Mostrar"]')
mostrar_button.click()

# Allow the page to load results
time.sleep(3)

# Function to scrape data from a single page
def scrape_page():
    items = driver.find_elements(By.CLASS_NAME, "item")  # Assuming 'item' is the class for listings
    for item in items:
        title = item.find_element(By.CLASS_NAME, 'title').text
        price = item.find_element(By.CLASS_NAME, 'price').text
        location = item.find_element(By.CLASS_NAME, 'location').text
        print(f"Title: {title}, Price: {price}, Location: {location}")

# Scrape the first page
scrape_page()

# Navigate through all available pages
while True:
    try:
        # Check if there is a "Next" button and click it
        next_button = driver.find_element(By.XPATH, '//a[text()="Siguiente"]')  # Replace with actual button text
        next_button.click()
        time.sleep(3)  # Wait for the new page to load
        scrape_page()  # Scrape the new page
    except Exception as e:
        print("No more pages or error:", e)
        break

# Close the browser
driver.quit()
