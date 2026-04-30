import asyncio
import os

from playwright.async_api import async_playwright


async def convert_svg_to_png():
    svg_path = os.path.abspath('diagrams/data_pipeline.svg')
    png_path = os.path.abspath('diagrams/data_pipeline.png')

    svg_path_f = svg_path.replace('\\', '/')
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 0; background: transparent; }}
            img {{ display: block; }}
        </style>
    </head>
    <body>
        <img src="file:///{svg_path_f}" />
    </body>
    </html>
    """

    html_file = os.path.abspath('diagrams/temp.html')
    html_file_f = html_file.replace('\\', '/')
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1200, "height": 600})
        await page.goto(f"file:///{html_file_f}")
        # Wait a bit to ensure SVG renders fully, including embedded HTML
        await page.wait_for_timeout(1000)
        # Take a high quality screenshot
        await page.screenshot(path=png_path, omit_background=True)
        await browser.close()

    os.remove(html_file)
    print(f"Successfully converted SVG to {png_path}")

if __name__ == '__main__':
    asyncio.run(convert_svg_to_png())
