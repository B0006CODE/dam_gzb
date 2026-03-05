// Reservoir data types

export interface Reservoir {
    id: string;
    name: string;
    province: string;
    city?: string;
    county?: string;
    location: string;
    coordinates?: [number, number]; // [longitude, latitude]
    basin?: string;
    type?: string; // 大型 or 中型
    capacity?: number; // 总库容（万方）
    damType?: string; // 主坝坝型
    maxHeight?: number; // 最大坝高（m）
}

export interface ProvinceStats {
    totalCount: number;
    reservoirs: string[]; // Array of reservoir IDs
    damTypes: Record<string, number>;
    basins: Record<string, number>;
}

export interface ProvinceStatsMap {
    [province: string]: ProvinceStats;
}

const DATA_BASE_URL = import.meta.env.BASE_URL || '/';

// Helper functions to load data
export async function loadReservoirs(): Promise<Reservoir[]> {
    const response = await fetch(`${DATA_BASE_URL}data/reservoirs.json`);
    return response.json();
}

export async function loadProvinceStats(): Promise<ProvinceStatsMap> {
    const response = await fetch(`${DATA_BASE_URL}data/provinceStats.json`);
    return response.json();
}

export function getReservoirsByProvince(reservoirs: Reservoir[], province: string): Reservoir[] {
    return reservoirs.filter(r => r.province === province);
}
