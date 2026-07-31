export interface HazardType {
  id: string;
  name: string;
  nameEn: string;
  icon: string;
  color: string;
  description: string;
  leadTimes: number[];
}

export const hazards: HazardType[] = [
  {
    id: 'heavy-rain',
    name: '暴雨',
    nameEn: 'Heavy Rain',
    icon: 'ri-showers-line',
    color: '#0d9488',
    description: '短时强降水可能引发城市内涝和山洪灾害',
    leadTimes: [3, 6, 12, 24, 48],
  },
  {
    id: 'extreme-heat',
    name: '极端高温',
    nameEn: 'Extreme Heat',
    icon: 'ri-sun-line',
    color: '#ea580c',
    description: '持续高温天气对人体健康和能源供应构成威胁',
    leadTimes: [24, 48, 72],
  },
  {
    id: 'flash-flood',
    name: '山洪',
    nameEn: 'Flash Flood',
    icon: 'ri-flood-line',
    color: '#dc2626',
    description: '山区短时强降水导致的突发性洪水',
    leadTimes: [1, 3, 6, 12],
  },
  {
    id: 'severe-convection',
    name: '强对流',
    nameEn: 'Severe Convection',
    icon: 'ri-thunderstorms-line',
    color: '#b45309',
    description: '雷暴大风、冰雹等强对流天气',
    leadTimes: [1, 3, 6],
  },
  {
    id: 'dust-storm',
    name: '沙尘暴',
    nameEn: 'Dust Storm',
    icon: 'ri-windy-line',
    color: '#a16207',
    description: '强风携带大量沙尘导致能见度急剧下降',
    leadTimes: [6, 12, 24, 48],
  },
];