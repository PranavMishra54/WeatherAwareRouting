import 'leaflet'

declare module 'leaflet' {
  interface HeatLayerOptions extends LayerOptions {
    radius?: number
    blur?: number
    maxZoom?: number
    max?: number
    minOpacity?: number
    gradient?: Record<number, string>
  }

  interface HeatLayer extends Layer {
    setLatLngs(latlngs: Array<[number, number, number]>): this
    setOptions(options: HeatLayerOptions): this
  }

  function heatLayer(
    latlngs: Array<[number, number, number]>,
    options?: HeatLayerOptions,
  ): HeatLayer
}
