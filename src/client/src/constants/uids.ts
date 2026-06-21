/** 约定测试用户 UID */
export const PRESET_UIDS = ['6000001', '6000002', '6000003'] as const;

export type PresetUid = (typeof PRESET_UIDS)[number];

export function randomPresetUid(): PresetUid {
  const i = Math.floor(Math.random() * PRESET_UIDS.length);
  return PRESET_UIDS[i];
}
