import { useQuery } from '@tanstack/react-query';
import api from '../api';

/** Whether LogoSphere can send email: undefined until known. A failed look doesn't say it can't: the server answers the form. */
export function useMailOn() {
    const { data, isError } = useQuery({
        queryKey: ['mail'],
        queryFn: () => api.get('/api/mail').then((r) => !!r.data.on),
        staleTime: 5 * 60_000,
        retry: 1,
    });
    return data === undefined && isError ? true : data;
}
