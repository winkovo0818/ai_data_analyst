import React from 'react';
import ReactECharts from 'echarts-for-react';

const ChartDisplay = ({ chart }) => {
  if (!chart || !chart.option) {
    return null;
  }

  return (
    <div className="chart-container-wrapper">
      <ReactECharts
        option={chart.option}
        style={{ height: '400px', width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
        theme={"macarons"} 
      />
    </div>
  );
};

export default ChartDisplay;
