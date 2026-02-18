import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Ruta del HTML de Acceso
        html_path = 'file:///' + os.path.abspath('Acceso_Hotmart.html').replace('\\', '/')
        pdf_path = 'Acceso_Dominio_Total.pdf'
        
        print(f"Generando Llave de Acceso desde: {html_path}")
        
        await page.goto(html_path)
        
        # Generar PDF (Formato Carta o A4, sin márgenes para que se vea full black)
        await page.pdf(
            path=pdf_path, 
            format="A4", 
            print_background=True, 
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"}
        )
        
        await browser.close()
        print(f"✅ ¡Llave de Acceso Generada! -> {os.path.abspath(pdf_path)}")

if __name__ == "__main__":
    asyncio.run(main())
