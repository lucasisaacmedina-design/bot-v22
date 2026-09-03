# LOBO V34.9 - PULIDO FINAL - LEGENDAS TRADINGVIEW
# Solo cambia el legend - lo demás igual que tu foto que ya está perfecta
# Cambia en tu main.py estas 2 lineas en el JS:

  legend: {
    show:true, 
    position:'bottom',
    labels:{colors:'#868993'},
    markers:{width:10, height:10, radius:2},
    fontSize:'10px'
  },

# Y en series pon:
  series: [
    {name: 'BTC/USDT', type: 'candlestick', data: ...},
    {name: 'EMA 9', type: 'line', data: ...},
    {name: 'EMA 21', type: 'line', data: ...}
  ],

# Agrega esto para que no diga series-1:
  dataLabels:{enabled:false}
