from playwright.sync_api import sync_playwright
import time
import os


def generar_pdf_resumen(
    url: str = "http://localhost:8501",
    output_path: str = "resumen_inflacion.pdf"
) -> None:
    """
    Genera un PDF de una sola página (altura completa) para resumen_v1.py.

    Usa el mismo enfoque del script de referencia:
    - Una sola página larga.
    - Ancho fijo de 1300px.
    - Altura dinámica calculada desde el DOM.
    - device_scale_factor=1 para evitar que las gráficas salgan cortadas.
    """

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with sync_playwright() as p:
        print("🤖 Iniciando navegador Chromium (Headless)...")

        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = browser.new_context(
            viewport={"width": 1400, "height": 1080},
            device_scale_factor=1
        )

        page = context.new_page()

        def scroll_to_load_all():
            """
            Hace scroll hacia abajo y hacia arriba intentando forzar el renderizado
            de componentes que puedan estar fuera de pantalla.
            """
            page.evaluate("""
                () => {
                    const scrollers = [
                        document.querySelector('[data-testid="stMain"]'),
                        document.querySelector('.main'),
                        document.scrollingElement,
                        document.documentElement,
                        document.body
                    ].filter(Boolean);

                    const bodyHeight = document.body ? document.body.scrollHeight : 0;
                    const docHeight = document.documentElement ? document.documentElement.scrollHeight : 0;
                    const target = Math.max(bodyHeight, docHeight);

                    scrollers.forEach(el => {
                        try {
                            el.scrollTop = target;
                        } catch (e) {}
                    });

                    try {
                        window.scrollTo(0, target);
                    } catch (e) {}
                }
            """)

            time.sleep(2)

            page.evaluate("""
                () => {
                    const scrollers = [
                        document.querySelector('[data-testid="stMain"]'),
                        document.querySelector('.main'),
                        document.scrollingElement,
                        document.documentElement,
                        document.body
                    ].filter(Boolean);

                    scrollers.forEach(el => {
                        try {
                            el.scrollTop = 0;
                        } catch (e) {}
                    });

                    try {
                        window.scrollTo(0, 0);
                    } catch (e) {}
                }
            """)

            time.sleep(1)

        embed_url = url if "embed=true" in url else f"{url}&embed=true" if "?" in url else f"{url}?embed=true"
        print(f"🌐 Cargando {embed_url} ...")
        page.goto(embed_url, wait_until="domcontentloaded")

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        # Esperar el contenido principal del resumen de inflación
        page.wait_for_selector("h1", state="visible", timeout=60000)
        page.wait_for_selector(".metric-card", state="visible", timeout=60000)
        page.wait_for_selector(".js-plotly-plot", state="visible", timeout=60000)

        # Pausa para dejar que Plotly termine de dibujar animaciones iniciales
        time.sleep(3)

        # Primer scroll para ayudar a renderizar componentes fuera de pantalla
        scroll_to_load_all()

        print("🧹 Inyectando CSS de limpieza para exportación...")

        css_limpieza = """
            /* Ocultar sidebar y chrome de Streamlit */
            [data-testid="stSidebar"],
            [data-testid="stSidebarCollapsedControl"],
            [data-testid="stSidebarResizeControl"],
            header[data-testid="stHeader"],
            footer,
            .stAppDeployButton,
            #MainMenu,
            [data-testid="stDecoration"],
            [data-testid="stToolbar"],
            [data-testid="stStatusWidget"],
            .floating-download-btn,
            .floating-warning {
                display: none !important;
            }

            /* Dejar el documento como una página continua */
            html, body, .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"],
            .main {
                height: auto !important;
                min-height: 100% !important;
                overflow: visible !important;
                position: static !important;
            }

            /* Contenedor principal del contenido */
            [data-testid="stAppViewBlockContainer"],
            .block-container,
            [data-testid="block-container"] {
                max-width: 100% !important;
                padding: 2rem !important;
                margin: 0 !important;
            }

            .stApp {
                background-color: #F8FAFC !important;
            }

            /* En una sola página larga no queremos forzar saltos de página */
            .metric-card,
            .chart-title,
            [data-testid="stPlotlyChart"],
            .js-plotly-plot,
            .plotly {
                break-inside: auto !important;
                page-break-inside: auto !important;
            }

            /* Permitir que elementos de Plotly no queden recortados por contenedores */
            [data-testid="stPlotlyChart"],
            .js-plotly-plot,
            .plotly {
                overflow: visible !important;
            }
        """

        page.add_style_tag(content=css_limpieza)
        time.sleep(1)

        # Forzar a Plotly a recalcular el ancho real de todas las gráficas tras aplicar el CSS
        page.evaluate("""
            () => {
                window.dispatchEvent(new Event('resize'));
                const plots = document.querySelectorAll('.js-plotly-plot');
                plots.forEach(p => {
                    if (window.Plotly && window.Plotly.Plots) {
                        window.Plotly.Plots.resize(p);
                    }
                });
            }
        """)
        time.sleep(1.5)

        # Respaldo para ocultar nudges/banners flotantes de Streamlit por texto
        page.evaluate("""
            () => {
                const FRASES_A_OCULTAR = [
                    "help agents write better apps",
                    "install the official streamlit skills",
                    "ai coding agents can build and debug your apps",
                ];

                const candidatos = document.querySelectorAll("body *");

                candidatos.forEach(el => {
                    if (el.children.length > 0) return;

                    const texto = (el.innerText || el.textContent || "").trim().toLowerCase();
                    if (!texto) return;

                    if (FRASES_A_OCULTAR.some(f => texto.includes(f))) {
                        const contenedor = el.closest('[data-testid], div, section') || el;
                        contenedor.style.setProperty("display", "none", "important");
                    }
                });
            }
        """)

        time.sleep(1)

        # Segundo scroll ya con el CSS de exportación aplicado
        scroll_to_load_all()

        time.sleep(2)

        altura_total = int(
            page.evaluate(
                "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, document.body.offsetHeight)"
            )
        )

        ancho_fijo = 1400

        # page.pdf() cambia el media type a "print" internamente justo antes
        # de capturar, lo que fuerza a Chromium a re-renderizar el layout con
        # reglas distintas a las de pantalla (de ahí el corrimiento de la
        # leyenda que no se ve hasta el PDF final). Forzamos "screen" para
        # que capture exactamente el mismo layout que ya validamos.
        page.emulate_media(media="screen")

        print(f"📄 Generando PDF de una sola página en: {output_path}")
        print(f"   Altura calculada: {altura_total}px")

        page.pdf(
            path=output_path,
            print_background=True,
            width=f"{ancho_fijo}px",
            height=f"{altura_total + 100}px",
            margin={
                "top": "0px",
                "bottom": "0px",
                "left": "0px",
                "right": "0px"
            }
        )

        browser.close()

        print(f"✅ ¡Listo! PDF generado en: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    salida = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "pdf",
        "resumen_inflacion.pdf"
    )

    generar_pdf_resumen(
        url="http://localhost:8501",
        output_path=salida
    )