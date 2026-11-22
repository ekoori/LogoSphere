import { useQuery } from '@tanstack/react-query';
import api from '../api';

/** Whether LogoSphere can send email: undefined until known, false if asking failed. */
export function useMailOn() {
    const { data, isError } = useQuery({
        queryKey: ['mail'],
        queryFn: () => api.get('/api/mail').then((r) => !!r.data.on),
        staleTime: 5 * 60_000,
        retry: 1,
    });
    return isError ? false : data;
}
