import os
from playwright.sync_api import sync_playwright

def generate_pdf():
    # Ruta absoluta al archivo HTML
    base_path = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_path, 'Ebook_Para_Generar.html')
    pdf_path = os.path.join(base_path, 'Ebook_Dominio_Total.pdf')
    
    # URL de archivo local
    file_url = f"file:///{html_path.replace(os.sep, '/')}"

    print(f"Generando PDF desde: {file_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Cargar la página
        page.goto(file_url)
        # Esperar un poco para asegurar que las imágenes carguen
        page.wait_for_timeout(2000)
        
        # Generar PDF
        # print_background=True es CLAVE para que salga la portada y los colores
        # scale=1 asegura que el tamaño sea correcto
        page.pdf(
            path=pdf_path, 
            format="A4", 
            print_background=True, 
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            scale=1
        )
        
        browser.close()
        
    print(f"✅ ¡PDF Generado con éxito! -> {pdf_path}")

if __name__ == "__main__":
    generate_pdf()
