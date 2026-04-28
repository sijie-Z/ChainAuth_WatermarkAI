/**
 * 前端图表配置
 */
import * as echarts from 'echarts'

/**
 * 资产统计图表
 */
export function createAssetStatsChart(data) {
  return {
    title: {
      text: '资产统计'
    },
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '资产类型',
        type: 'pie',
        radius: '50%',
        data: [
          { value: data.image, name: '影像' },
          { value: data.model, name: '三维模型' },
          { value: data.vector, name: '矢量数据' },
          { value: data.document, name: '文献' },
          { value: data.video, name: '视频' }
        ]
      }
    ]
  }
}

/**
 * 水印处理趋势图表
 */
export function createWatermarkTrendChart(data) {
  return {
    title: {
      text: '水印处理趋势'
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: data.dates
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '嵌入',
        type: 'line',
        data: data.embedCount,
        smooth: true
      },
      {
        name: '提取',
        type: 'line',
        data: data.extractCount,
        smooth: true
      }
    ]
  }
}

/**
 * 授权类型分布图表
 */
export function createLicenseTypeChart(data) {
  return {
    title: {
      text: '授权类型分布'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: ['个人', '学术', '商业', '展览', '衍生']
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        type: 'bar',
        data: [
          data.personal,
          data.academic,
          data.commercial,
          data.display,
          data.derivative
        ],
        itemStyle: {
          color: '#409eff'
        }
      }
    ]
  }
}

/**
 * 区块链存证统计图表
 */
export function createBlockchainStatsChart(data) {
  return {
    title: {
      text: '区块链存证统计'
    },
    tooltip: {
      trigger: 'item'
    },
    series: [
      {
        name: '存证状态',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'center'
        },
        data: [
          { value: data.confirmed, name: '已确认' },
          { value: data.pending, name: '待确认' }
        ]
      }
    ]
  }
}

/**
 * 园林资产分布地图
 */
export function createGardenMapChart(data) {
  return {
    title: {
      text: '园林资产分布'
    },
    tooltip: {
      trigger: 'item'
    },
    visualMap: {
      min: 0,
      max: 100,
      left: 'left',
      top: 'bottom',
      text: ['高', '低'],
      calculable: true
    },
    series: [
      {
        name: '资产数量',
        type: 'map',
        roam: true,
        data: data.map(item => ({
          name: item.gardenName,
          value: item.assetCount
        }))
      }
    ]
  }
}

/**
 * 初始化图表
 */
export function initChart(el, option) {
  const chart = echarts.init(el)
  chart.setOption(option)
  return chart
}

/**
 * 响应式调整
 */
export function resizeChart(chart) {
  window.addEventListener('resize', () => {
    chart.resize()
  })
}