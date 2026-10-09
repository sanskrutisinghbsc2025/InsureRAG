import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

export const api = {
    getSystemStatus: () => axios.get(`${API_URL}/system`).then(res => res.data),
    
    uploadFile: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return axios.post(`${API_URL}/upload`, formData).then(res => res.data);
    },
    
    queryDocument: (docPath: string, query: string, apiKey?: string) => 
        axios.post(`${API_URL}/query`, { doc_path: docPath, query, api_key: apiKey }).then(res => res.data),

    getJourney: (docPath: string, query?: string) =>
        axios.post(`${API_URL}/pipeline/journey`, { doc_path: docPath, query }).then(res => res.data),

    updateKeys: (apiKeys: string) =>
        axios.post(`${API_URL}/keys`, { api_keys: apiKeys }).then(res => res.data),

    getCacheStats: () => axios.get(`${API_URL}/cache/stats`).then(res => res.data),

    clearCache: () => axios.post(`${API_URL}/cache/clear`).then(res => res.data)
};
