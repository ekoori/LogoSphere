// Whether the viewer is in Simple (utils/modes.js says what that means).
import { useLogin } from '../App';
import { SIMPLE } from './modes';

export const useSimple = () => useLogin().uiMode === SIMPLE;
