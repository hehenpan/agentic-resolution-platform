import { describe, it, expect, beforeEach } from 'vitest';
import { getCookie, setCookie, removeCookie } from './cookie';

describe('cookie utility', () => {
  beforeEach(() => {
    // Clear cookies before each test
    document.cookie.split(';').forEach((c) => {
      document.cookie = c
        .replace(/^ +/, '')
        .replace(/=.*/, '=;expires=' + new Date(0).toUTCString() + ';path=/');
    });
  });

  it('sets and gets cookie correctly', () => {
    setCookie('sessionid', 'mock_session_123');
    expect(getCookie('sessionid')).toBe('mock_session_123');
  });

  it('returns null for non-existent cookie', () => {
    expect(getCookie('sessionid')).toBeNull();
  });

  it('removes cookie correctly', () => {
    setCookie('sessionid', 'mock_session_123');
    expect(getCookie('sessionid')).toBe('mock_session_123');
    removeCookie('sessionid');
    expect(getCookie('sessionid')).toBeNull();
  });
});
