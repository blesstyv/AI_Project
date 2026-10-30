
import unicodedata
from difflib import get_close_matches

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder


# Catálogo de ejemplo.
# Los precios y especificaciones son datos demostrativos.
PRODUCTOS = pd.DataFrame([
    {
        "producto": "Galaxy S25",
        "categoria": "smartphone",
        "marca": "Samsung",
        "sistema_operativo": "Android",
        "precio": 799,
        "ram_gb": 12,
        "almacenamiento_gb": 256,
        "pantalla_pulgadas": 6.2,
    },
    {
        "producto": "Pixel 10",
        "categoria": "smartphone",
        "marca": "Google",
        "sistema_operativo": "Android",
        "precio": 749,
        "ram_gb": 12,
        "almacenamiento_gb": 256,
        "pantalla_pulgadas": 6.3,
    },
    {
        "producto": "iPhone 17",
        "categoria": "smartphone",
        "marca": "Apple",
        "sistema_operativo": "iOS",
        "precio": 899,
        "ram_gb": 8,
        "almacenamiento_gb": 256,
        "pantalla_pulgadas": 6.3,
    },
    {
        "producto": "MacBook Air 13",
        "categoria": "laptop",
        "marca": "Apple",
        "sistema_operativo": "macOS",
        "precio": 1099,
        "ram_gb": 16,
        "almacenamiento_gb": 512,
        "pantalla_pulgadas": 13.6,
    },
    {
        "producto": "Dell XPS 13",
        "categoria": "laptop",
        "marca": "Dell",
        "sistema_operativo": "Windows",
        "precio": 1199,
        "ram_gb": 16,
        "almacenamiento_gb": 512,
        "pantalla_pulgadas": 13.4,
    },
    {
        "producto": "Lenovo Yoga Slim 7",
        "categoria": "laptop",
        "marca": "Lenovo",
        "sistema_operativo": "Windows",
        "precio": 999,
        "ram_gb": 16,
        "almacenamiento_gb": 512,
        "pantalla_pulgadas": 14.0,
    },
    {
        "producto": "iPad Air",
        "categoria": "tablet",
        "marca": "Apple",
        "sistema_operativo": "iPadOS",
        "precio": 599,
        "ram_gb": 8,
        "almacenamiento_gb": 256,
        "pantalla_pulgadas": 11.0,
    },
    {
        "producto": "Galaxy Tab S10",
        "categoria": "tablet",
        "marca": "Samsung",
        "sistema_operativo": "Android",
        "precio": 649,
        "ram_gb": 12,
        "almacenamiento_gb": 256,
        "pantalla_pulgadas": 11.0,
    },
    {
        "producto": "Lenovo Tab P12",
        "categoria": "tablet",
        "marca": "Lenovo",
        "sistema_operativo": "Android",
        "precio": 349,
        "ram_gb": 8,
        "almacenamiento_gb": 128,
        "pantalla_pulgadas": 12.7,
    },
])


# Características numéricas utilizadas en las recomendaciones.
COLUMNAS_NUMERICAS = [
    "precio",
    "ram_gb",
    "almacenamiento_gb",
    "pantalla_pulgadas",
]


def normalizar_texto(texto: str) -> str:
    """
    Normaliza el texto ingresado por el usuario.
    Ignora mayúsculas, acentos y espacios adicionales.
    """
    texto = " ".join(texto.strip().casefold().split())

    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


def recomendar_productos(
    nombre_producto: str,
    cantidad: int = 3
) -> pd.DataFrame:
    """
    Busca productos similares utilizando sus características.
    Devuelve los resultados ordenados por similitud del coseno.
    """

    if cantidad < 1:
        raise ValueError(
            "La cantidad de recomendaciones debe ser al menos 1."
        )

    # Normalizar los nombres para facilitar la búsqueda.
    nombres_normalizados = PRODUCTOS["producto"].map(
        normalizar_texto
    )

    coincidencias = PRODUCTOS.index[
        nombres_normalizados == normalizar_texto(nombre_producto)
    ]

    # Verificar que el producto exista.
    if coincidencias.empty:
        sugerencias = get_close_matches(
            normalizar_texto(nombre_producto),
            nombres_normalizados.tolist(),
            n=1,
            cutoff=0.5
        )

        mensaje = f"No se encontró el producto: {nombre_producto}"

        if sugerencias:
            indice = nombres_normalizados[
                nombres_normalizados == sugerencias[0]
            ].index[0]

            mensaje += (
                f". ¿Quisiste decir "
                f"'{PRODUCTOS.loc[indice, 'producto']}'?"
            )

        raise ValueError(mensaje)

    # Preparar las características para calcular similitudes.
    #
    # OneHotEncoder convierte categorías en valores de 0 y 1.
    # MinMaxScaler escala las variables numéricas entre 0 y 1.
    #
    # Damos mayor importancia a la categoría para favorecer
    # recomendaciones de productos del mismo tipo.

    preprocesador = ColumnTransformer(
        transformers=[
            (
                "categoria",
                OneHotEncoder(handle_unknown="ignore"),
                ["categoria"]
            ),
            (
                "marca",
                OneHotEncoder(handle_unknown="ignore"),
                ["marca"]
            ),
            (
                "sistema",
                OneHotEncoder(handle_unknown="ignore"),
                ["sistema_operativo"]
            ),
            (
                "numericas",
                MinMaxScaler(),
                COLUMNAS_NUMERICAS
            ),
        ],
        transformer_weights={
            "categoria": 3.0,
            "marca": 0.7,
            "sistema": 0.7,
            "numericas": 1.0,
        },
    )

    # Transformar los datos de los productos.
    matriz_caracteristicas = preprocesador.fit_transform(
        PRODUCTOS
    )

    # Identificar el producto seleccionado.
    indice_producto = int(coincidencias[0])

    # Calcular la similitud del coseno entre los productos.
    similitudes = cosine_similarity(
        matriz_caracteristicas
    )[indice_producto]

    # Excluir el producto seleccionado.
    recomendaciones = PRODUCTOS.drop(
        index=indice_producto
    ).copy()

    # Incorporar la puntuación de similitud.
    recomendaciones["similitud"] = similitudes[
        recomendaciones.index
    ]

    # Definir las columnas que verá el usuario.
    columnas_resultado = [
        "producto",
        "categoria",
        "marca",
        "precio",
        "similitud",
    ]

    # Ordenar y seleccionar las mejores recomendaciones.
    return (
        recomendaciones.nlargest(
            min(cantidad, len(recomendaciones)),
            "similitud"
        )[columnas_resultado]
        .reset_index(drop=True)
    )


def main() -> None:
    """
    Muestra los productos disponibles y permite al usuario
    obtener recomendaciones desde la terminal.
    """

    print("Productos disponibles:")

    for nombre in PRODUCTOS["producto"]:
        print(f"- {nombre}")

    # Solicitar el producto al usuario.
    seleccionado = input(
        "\nEscribe el nombre del producto que te interesa: "
    ).strip()

    # Validar que el usuario haya escrito algo.
    if not seleccionado:
        print("Debes escribir el nombre de un producto.")
        return

    # Obtener las recomendaciones.
    try:
        recomendaciones = recomendar_productos(
            seleccionado
        )

    except ValueError as error:
        print(error)
        return

    # Mostrar los resultados en la terminal.
    print(
        f"\nTres productos más similares a {seleccionado}:"
    )

    print(
        recomendaciones.to_string(
            index=False,
            formatters={
                "similitud": lambda valor: f"{valor:.3f}"
            },
        )
    )

    print(
        "\nNota: la similitud es una medida matemática, "
        "no un porcentaje de compra."
    )


# Ejecutar el programa.
if __name__ == "__main__":
    main()
