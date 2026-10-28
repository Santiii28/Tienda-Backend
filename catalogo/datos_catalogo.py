"""Catálogo de demostración de Taller Nogal.

Son datos de ejemplo para que la tienda tenga qué mostrar: los nombres, precios
(en pesos colombianos) y existencias no vienen de un inventario real. Se cargan
con `python manage.py cargar_catalogo`.

Cada producto tiene un nombre de archivo de foto; la foto se sirve desde la
carpeta `public/productos/` del frontend con la ruta "/productos/<archivo>.jpg".
Solo se asigna la foto a los productos cuyo archivo ya existe (FOTOS_LISTAS);
los demás quedan sin imagen y la tarjeta muestra su letra inicial.
"""

# (nombre, categoría, precio, existencias, descripción, archivo de la foto)
PRODUCTOS = [
    # --- Silla ---
    ("Silla de comedor tapizada", "Silla", 135000, 12,
     "Silla de comedor con asiento tapizado y patas de madera.", "silla-de-comedor-tapizada"),
    ("Silla de madera clásica", "Silla", 98000, 15,
     "Silla de madera de líneas sencillas para comedor o cocina.", "silla-de-madera-clasica"),
    ("Butaco de bar", "Silla", 119000, 8,
     "Butaco alto para barra o mesón de cocina.", "butaco-de-bar"),
    ("Mecedora de madera", "Silla", 289000, 3,
     "Mecedora de madera para la sala o la terraza.", "mecedora-de-madera"),
    # --- Sala ---
    ("Sofá de tres puestos", "Sala", 1490000, 3,
     "Sofá de tres puestos con cojines y tapizado suave.", "sofa-de-tres-puestos"),
    ("Sillón individual", "Sala", 650000, 5,
     "Sillón cómodo para la sala o un rincón de lectura.", "sillon-individual"),
    ("Mesa de centro", "Sala", 280000, 7,
     "Mesa de centro de madera para la sala.", "mesa-de-centro"),
    ("Mueble para televisor", "Sala", 520000, 4,
     "Mueble bajo con espacio para el televisor y repisas.", "mueble-para-televisor"),
    # --- Comedor ---
    ("Comedor de seis puestos", "Comedor", 1850000, 2,
     "Mesa rectangular de madera con seis sillas.", "comedor-de-seis-puestos"),
    ("Mesa redonda de cocina", "Comedor", 420000, 6,
     "Mesa redonda para cuatro personas, ideal para cocinas y espacios pequeños.", "mesa-redonda-de-cocina"),
    ("Aparador", "Comedor", 780000, 0,
     "Aparador de madera con puertas y cajones para guardar vajilla.", "aparador"),
    # --- Dormitorio ---
    ("Cama doble con cabecero", "Dormitorio", 1150000, 4,
     "Cama doble con cabecero de madera.", "cama-doble-con-cabecero"),
    ("Mesa de noche", "Dormitorio", 190000, 14,
     "Mesa de noche con un cajón.", "mesa-de-noche"),
    ("Cómoda de cuatro cajones", "Dormitorio", 690000, 5,
     "Cómoda de cuatro cajones para guardar ropa.", "comoda-de-cuatro-cajones"),
    ("Closet de dos puertas", "Dormitorio", 960000, 3,
     "Closet de dos puertas con espacio para colgar ropa y repisas.", "closet-de-dos-puertas"),
    # --- Oficina ---
    ("Escritorio de madera", "Oficina", 450000, 9,
     "Escritorio de madera con cajón para estudiar o trabajar en casa.", "escritorio-de-madera"),
    ("Escritorio clásico", "Oficina", 590000, 4,
     "Escritorio de madera de líneas sencillas con dos cajones.", "escritorio-clasico"),
    ("Silla giratoria de escritorio", "Oficina", 340000, 10,
     "Silla giratoria con ruedas para el escritorio.", "silla-giratoria-de-escritorio"),
    # --- Almacenamiento ---
    ("Estantería de cinco repisas", "Almacenamiento", 310000, 8,
     "Estantería de madera con cinco repisas.", "estanteria-de-cinco-repisas"),
    ("Zapatero de madera", "Almacenamiento", 175000, 11,
     "Zapatero con repisas para ordenar el calzado en la entrada.", "zapatero-de-madera"),
    ("Baúl de madera", "Almacenamiento", 230000, 6,
     "Baúl de madera para guardar cobijas y otros objetos.", "baul-de-madera"),
    # --- Decoración e iluminación ---
    ("Lámpara de pie", "Decoración e iluminación", 210000, 9,
     "Lámpara de pie para la sala o el dormitorio.", "lampara-de-pie"),
    ("Espejo redondo de pared", "Decoración e iluminación", 165000, 13,
     "Espejo redondo con marco de madera.", "espejo-redondo-de-pared"),
    ("Repisa flotante", "Decoración e iluminación", 85000, 20,
     "Repisa de pared para libros y adornos.", "repisa-flotante"),
]


# Ofertas de demostración: archivo de la foto -> precio anterior (se muestra tachado).
# Son datos de ejemplo para probar la tienda; no son promociones reales.
PRECIOS_ANTERIORES = {
    "sofa-de-tres-puestos": 1690000,
    "mesa-de-centro": 320000,
    "lampara-de-pie": 245000,
    "silla-de-comedor-tapizada": 155000,
}


# Archivos de foto que ya están en `public/productos/` del frontend.
FOTOS_LISTAS = {
    "sofa-de-tres-puestos", "sillon-individual", "mesa-de-centro",
    "mueble-para-televisor", "comedor-de-seis-puestos", "cama-doble-con-cabecero",
    "mesa-de-noche", "comoda-de-cuatro-cajones", "escritorio-de-madera",
    "escritorio-clasico", "silla-giratoria-de-escritorio",
    "estanteria-de-cinco-repisas", "baul-de-madera", "repisa-flotante",
    "butaco-de-bar", "lampara-de-pie", "mecedora-de-madera",
    "silla-de-madera-clasica", "espejo-redondo-de-pared",
    "silla-de-comedor-tapizada", "mesa-redonda-de-cocina",
}
