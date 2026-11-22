// What AI help is switched on, and what is left of the member's day.
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../api';
import { useLogin } from '../App';

const KEY = ['ai-help'];

/** kind: 'pictures' or 'value_cards'. Off until the server says it's on. */
export function useAiHelp(kind) {
    const { userId } = useLogin();
    const client = useQueryClient();
    const { data } = useQuery({
        queryKey: [...KEY, userId],
        queryFn: () => api.get('/api/ai').then((r) => r.data),
        enabled: !!userId,
        staleTime: 60_000,
        retry: false,
    });
    const setLeft = (left) => client.setQueryData([...KEY, userId],
        (was) => was && ({ ...was, [kind]: { ...was[kind], left } }));
    return { on: !!data?.[kind]?.on, left: data?.[kind]?.left ?? 0, setLeft };
}
