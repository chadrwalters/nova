/// <reference path="../../types/global.d.ts" />
import { describe, expect, it } from '@jest/globals';
import { decimateData, loadProgressiveData, type DataPoint } from '../dataDecimation';

describe('Data Decimation Utils', () => {
  // Generate test data
  const generateTestData = (count: number): DataPoint[] => {
    const data: DataPoint[] = [];
    for (let i = 0; i < count; i++) {
      data.push({
        timestamp: i * 1000,
        value: Math.sin(i * 0.1) * 100 + Math.random() * 10,
      });
    }
    return data;
  };

  describe('decimateData', () => {
    it('should return original data if length is less than maxPoints', () => {
      const data = generateTestData(50);
      const result = decimateData(data, { maxPoints: 100 });
      expect(result).toEqual(data);
    });

    it('should reduce data points to maxPoints using LTTB', () => {
      const data = generateTestData(1000);
      const maxPoints = 100;
      const result = decimateData(data, { maxPoints, aggregation: 'LTTB' });
      expect(result.length).toBeLessThanOrEqual(maxPoints);
      expect(result[0]).toEqual(data[0]); // First point should be preserved
      expect(result[result.length - 1]).toEqual(data[data.length - 1]); // Last point should be preserved
    });

    it('should reduce data points using min-max aggregation', () => {
      const data = generateTestData(1000);
      const maxPoints = 100;
      const result = decimateData(data, { maxPoints, aggregation: 'min-max' });
      expect(result.length).toBeLessThanOrEqual(maxPoints);
    });

    it('should reduce data points using average aggregation', () => {
      const data = generateTestData(1000);
      const maxPoints = 100;
      const result = decimateData(data, { maxPoints, aggregation: 'average' });
      expect(result.length).toBeLessThanOrEqual(maxPoints);
    });

    it('should filter points based on minDistance', () => {
      const data = generateTestData(100);
      const minDistance = 5000; // 5 seconds
      const result = decimateData(data, { minDistance });
      expect(result.length).toBeLessThan(data.length);
      
      // Check that points are at least minDistance apart
      for (let i = 1; i < result.length; i++) {
        expect(result[i].timestamp - result[i - 1].timestamp).toBeGreaterThanOrEqual(minDistance);
      }
    });
  });

  describe('loadProgressiveData', () => {
    it('should return all data as initial if length is less than initialPoints', () => {
      const data = generateTestData(50);
      const { initial, remaining } = loadProgressiveData(data, { initialPoints: 100 });
      expect(initial).toEqual(data);
      expect(remaining).toEqual([]);
    });

    it('should split data into initial and remaining chunks', () => {
      const data = generateTestData(1000);
      const initialPoints = 100;
      const chunkSize = 200;
      const { initial, remaining } = loadProgressiveData(data, { initialPoints, chunkSize });
      
      expect(initial.length).toBeLessThanOrEqual(initialPoints);
      expect(remaining.length).toBeGreaterThan(0);
      expect(remaining[0].length).toBeLessThanOrEqual(chunkSize);
    });

    it('should respect maxPoints limit', () => {
      const data = generateTestData(5000);
      const maxPoints = 1000;
      const { initial, remaining } = loadProgressiveData(data, { maxPoints });
      
      const totalPoints = initial.length + remaining.reduce((sum, chunk) => sum + chunk.length, 0);
      expect(totalPoints).toBeLessThanOrEqual(maxPoints);
    });

    it('should preserve data order in chunks', () => {
      const data = generateTestData(1000);
      const { initial, remaining } = loadProgressiveData(data);
      
      let lastTimestamp = -Infinity;
      
      // Check initial chunk
      for (const point of initial) {
        expect(point.timestamp).toBeGreaterThan(lastTimestamp);
        lastTimestamp = point.timestamp;
      }
      
      // Check remaining chunks
      for (const chunk of remaining) {
        for (const point of chunk) {
          expect(point.timestamp).toBeGreaterThan(lastTimestamp);
          lastTimestamp = point.timestamp;
        }
      }
    });
  });
}); 