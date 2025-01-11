type DataPoint = {
  timestamp: string;
  [key: string]: string | number;
};

export function convertToCSV(data: DataPoint[]): string {
  if (data.length === 0) return '';

  // Get headers from the first data point
  const headers = Object.keys(data[0]);
  const csvHeader = headers.join(',');

  // Convert each data point to CSV row
  const csvRows = data.map(point => 
    headers.map(header => {
      const value = point[header];
      // Wrap strings in quotes, leave numbers as is
      return typeof value === 'string' ? `"${value}"` : value;
    }).join(',')
  );

  return [csvHeader, ...csvRows].join('\n');
}

export function downloadCSV(filename: string, csvContent: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  
  // Create a URL for the blob
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  
  // Append link, trigger download, and cleanup
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function formatMetricsData(
  timestamps: string[],
  metrics: { [key: string]: number[] }
): DataPoint[] {
  return timestamps.map((timestamp, index) => {
    const dataPoint: DataPoint = { timestamp };
    Object.entries(metrics).forEach(([key, values]) => {
      dataPoint[key] = values[index];
    });
    return dataPoint;
  });
} 