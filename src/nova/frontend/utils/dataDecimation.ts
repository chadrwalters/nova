export interface DataPoint {
  timestamp: number;
  value: number;
}

export interface DecimationOptions {
  maxPoints?: number;
  minDistance?: number;
  aggregation?: 'LTTB' | 'average' | 'min-max';
}

/**
 * Largest-Triangle-Three-Buckets (LTTB) algorithm for downsampling time series data
 * This algorithm preserves visual characteristics of the data while reducing points
 */
function downsampleLTTB(data: DataPoint[], targetPoints: number): DataPoint[] {
  if (data.length <= targetPoints) return data;

  const result: DataPoint[] = [];
  const bucketSize = (data.length - 2) / (targetPoints - 2);

  // Always add the first point
  result.push(data[0]);

  // Process all buckets except the last one
  for (let i = 0; i < targetPoints - 2; i++) {
    const bucketStart = Math.floor((i + 0) * bucketSize) + 1;
    const bucketEnd = Math.floor((i + 1) * bucketSize) + 1;
    const avgX = bucketStart + (bucketEnd - bucketStart) / 2;

    let maxArea = -1;
    let maxAreaPoint = data[bucketStart];
    const a = result[result.length - 1]; // Previous point
    const b = { timestamp: avgX, value: 0 }; // Average X of next bucket

    // Find point that creates the largest triangle with previous point and next bucket
    for (let j = bucketStart; j < bucketEnd; j++) {
      b.value = data[j].value;
      const area = Math.abs(
        (a.timestamp - data[j].timestamp) * (b.value - a.value) -
        (a.timestamp - b.timestamp) * (data[j].value - a.value)
      ) * 0.5;

      if (area > maxArea) {
        maxArea = area;
        maxAreaPoint = data[j];
      }
    }

    result.push(maxAreaPoint);
  }

  // Always add the last point
  result.push(data[data.length - 1]);

  return result;
}

/**
 * Min-max decimation algorithm that preserves peaks in the data
 */
function downsampleMinMax(data: DataPoint[], targetPoints: number): DataPoint[] {
  if (data.length <= targetPoints) return data;

  const result: DataPoint[] = [];
  const bucketSize = data.length / (targetPoints / 2); // We'll store min and max for each bucket

  // Process all buckets
  for (let i = 0; i < targetPoints / 2; i++) {
    const bucketStart = Math.floor(i * bucketSize);
    const bucketEnd = Math.floor((i + 1) * bucketSize);

    let minPoint = data[bucketStart];
    let maxPoint = data[bucketStart];

    // Find min and max points in the bucket
    for (let j = bucketStart; j < bucketEnd; j++) {
      if (data[j].value < minPoint.value) minPoint = data[j];
      if (data[j].value > maxPoint.value) maxPoint = data[j];
    }

    // Add points in the correct order (based on timestamp)
    if (minPoint.timestamp < maxPoint.timestamp) {
      result.push(minPoint, maxPoint);
    } else {
      result.push(maxPoint, minPoint);
    }
  }

  return result;
}

/**
 * Average decimation algorithm that smooths the data
 */
function downsampleAverage(data: DataPoint[], targetPoints: number): DataPoint[] {
  if (data.length <= targetPoints) return data;

  const result: DataPoint[] = [];
  const bucketSize = data.length / targetPoints;

  // Process all buckets
  for (let i = 0; i < targetPoints; i++) {
    const bucketStart = Math.floor(i * bucketSize);
    const bucketEnd = Math.floor((i + 1) * bucketSize);

    let sumValue = 0;
    let sumTimestamp = 0;
    const bucketCount = bucketEnd - bucketStart;

    // Calculate averages for the bucket
    for (let j = bucketStart; j < bucketEnd; j++) {
      sumValue += data[j].value;
      sumTimestamp += data[j].timestamp;
    }

    result.push({
      timestamp: Math.round(sumTimestamp / bucketCount),
      value: sumValue / bucketCount,
    });
  }

  return result;
}

/**
 * Decimate time series data based on specified options
 */
export function decimateData(
  data: DataPoint[],
  options: DecimationOptions = {}
): DataPoint[] {
  const {
    maxPoints = 1000,
    minDistance = 1,
    aggregation = 'LTTB'
  } = options;

  // Filter out points that are too close together
  if (minDistance > 1) {
    data = data.filter((point, index) => {
      if (index === 0) return true;
      return point.timestamp - data[index - 1].timestamp >= minDistance;
    });
  }

  // Apply downsampling algorithm
  switch (aggregation) {
    case 'LTTB':
      return downsampleLTTB(data, maxPoints);
    case 'min-max':
      return downsampleMinMax(data, maxPoints);
    case 'average':
      return downsampleAverage(data, maxPoints);
    default:
      return data;
  }
}

/**
 * Progressive data loading for large datasets
 */
export function loadProgressiveData(
  data: DataPoint[],
  options: {
    initialPoints?: number;
    chunkSize?: number;
    maxPoints?: number;
  } = {}
): {
  initial: DataPoint[];
  remaining: DataPoint[][];
} {
  const {
    initialPoints = 100,
    chunkSize = 500,
    maxPoints = 2000
  } = options;

  if (data.length <= initialPoints) {
    return { initial: data, remaining: [] };
  }

  // Get initial data with LTTB for best visual representation
  const initial = downsampleLTTB(data, initialPoints);

  // Split remaining data into chunks
  const remaining: DataPoint[][] = [];
  const totalChunks = Math.min(
    Math.ceil((data.length - initialPoints) / chunkSize),
    Math.ceil(maxPoints / chunkSize)
  );

  for (let i = 0; i < totalChunks; i++) {
    const start = initialPoints + i * chunkSize;
    const end = Math.min(start + chunkSize, data.length);
    remaining.push(data.slice(start, end));
  }

  return { initial, remaining };
} 