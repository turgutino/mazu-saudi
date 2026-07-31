export interface Region {
  id: string;
  name: string;
  nameEn: string;
  lat: number;
  lon: number;
  sensitivity: {
    flashFlood: 'high' | 'medium' | 'low';
    heatwave: 'high' | 'medium' | 'low';
    dustStorm: 'high' | 'medium' | 'low';
  };
}

export const regions: Region[] = [
  {
    id: 'jazan',
    name: '吉赞',
    nameEn: 'Jazan',
    lat: 16.8892,
    lon: 42.5511,
    sensitivity: { flashFlood: 'high', heatwave: 'medium', dustStorm: 'low' },
  },
  {
    id: 'riyadh',
    name: '利雅得',
    nameEn: 'Riyadh',
    lat: 24.7136,
    lon: 46.6753,
    sensitivity: { flashFlood: 'medium', heatwave: 'high', dustStorm: 'high' },
  },
  {
    id: 'jeddah',
    name: '吉达',
    nameEn: 'Jeddah',
    lat: 21.5433,
    lon: 39.1728,
    sensitivity: { flashFlood: 'high', heatwave: 'medium', dustStorm: 'medium' },
  },
  {
    id: 'makkah',
    name: '麦加',
    nameEn: 'Makkah',
    lat: 21.3891,
    lon: 39.8579,
    sensitivity: { flashFlood: 'high', heatwave: 'high', dustStorm: 'medium' },
  },
  {
    id: 'dammam',
    name: '达曼',
    nameEn: 'Dammam',
    lat: 26.4207,
    lon: 50.0888,
    sensitivity: { flashFlood: 'low', heatwave: 'high', dustStorm: 'high' },
  },
  {
    id: 'abha',
    name: '艾卜哈',
    nameEn: 'Abha',
    lat: 18.2164,
    lon: 42.5053,
    sensitivity: { flashFlood: 'medium', heatwave: 'low', dustStorm: 'low' },
  },
  {
    id: 'medina',
    name: '麦地那',
    nameEn: 'Medina',
    lat: 24.5247,
    lon: 39.5692,
    sensitivity: { flashFlood: 'medium', heatwave: 'high', dustStorm: 'medium' },
  },
  {
    id: 'tabuk',
    name: '塔布克',
    nameEn: 'Tabuk',
    lat: 28.3835,
    lon: 36.5771,
    sensitivity: { flashFlood: 'low', heatwave: 'medium', dustStorm: 'high' },
  },
];