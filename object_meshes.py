class ObjectMesh:
    def __init__(self, vertices, colors, faces_t=None, faces_q=None, edges=None):
        self.enableFaces = True
        self.enableEdges = True

        self.verticesVBO = vertices
        self.colorsFacesVBO = colors
        self.colorsEdgesVBO = colors  # Будет переопределено
        self.colorsHoveredVBO = colors
        self.colorsSelectedVBO = colors
        self.colorsEdgesActiveVBO = colors  # Будет переопределено

        self.facesQuads = faces_q
        self.facesTriangles = faces_t
        self.edges = edges

        self.enabled = True

    def on_hover(self):
        self.colorsEdgesActiveVBO = self.colorsHoveredVBO

    def on_unhover(self):
        self.colorsEdgesActiveVBO = self.colorsEdgesVBO  # Возвращаем цвет ребер