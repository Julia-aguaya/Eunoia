# Legacy recoverable turns blocked report

- Source JSON: `eunoia.recoverableturns.json`
- Blocked rows for manual review: **538**
- Affected student buckets: **202**
- Current matched rows in blocked set: **263**
- Orphan rows: **275**
- Students with multiple blocked rows: **116**
- Cases with secondary blockers hidden by importer order: **190**
- Scope: report only, no business logic changes.

## Breakdown by cause

- `ambiguous_section`: 262
- `inconsistent_state`: 1
- `orphan_user`: 275
- secondary `ambiguous_section`: 175
- secondary `inconsistent_state`: 1
- secondary `missing_section_mapping`: 15

### ambiguous_section

- `cadillac | reformer_abajo`: 131
- `reformer_arriba | reformer_abajo`: 131

### inconsistent_state

- `reformer_arriba | reformer_abajo`: 1

### orphan_user

- `cadillac | reformer_abajo`: 105
- `reformer_abajo`: 86
- `reformer_arriba | reformer_abajo`: 69

## Manual workflow

1. Start with `legacy_recoverableturns_blocked_report.csv` to filter by `blocking_cause`, student, or legacy user id.
2. Resolve `ambiguous_section` rows first using `possible_sections_label` plus the original day/hour.
3. Review `orphan_user` rows against the legacy user export (`legacy_user_email` / `legacy_user_name`) before deciding whether to import or discard.
4. Leave the single `inconsistent_state` row for explicit business confirmation before any backfill.

## Cases grouped by student

### Name unavailable - `6838ba6624d4d1b7adb00f99`

- legacy user id: `6838ba6624d4d1b7adb00f99`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `126` / recoverable `690bace487e38f361205b114` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-03T20:00:36.073000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `134` / recoverable `691247a818c10abc35d74912` / cause `orphan_user`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T20:14:32.437000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838bc0a24d4d1b7adb00fda`

- legacy user id: `6838bc0a24d4d1b7adb00fda`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `199` / recoverable `69437af1f61c580ccf4650ea` / cause `orphan_user`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-15T03:54:25.249000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `242` / recoverable `6989196af61c580ccf892254` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T23:16:58.765000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838be0a24d4d1b7adb0108e`

- legacy user id: `6838be0a24d4d1b7adb0108e`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `35` / recoverable `6898d449418f2e9a6b6f3569` / cause `orphan_user`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T17:18:01.741000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `52` / recoverable `68a528eec065187129bcde64` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T01:46:22.510000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `59` / recoverable `68b62640af1e42f64d251cf4` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T23:03:28.154000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838bf3a24d4d1b7adb010c0`

- legacy user id: `6838bf3a24d4d1b7adb010c0`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `97` / recoverable `68e4f17483c46bbb4eacb833` / cause `orphan_user`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T10:54:44.673000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `112` / recoverable `68f6d6693d5cf39df15718f5` / cause `orphan_user`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-20T00:40:09.157000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838c1f324d4d1b7adb012d6`

- legacy user id: `6838c1f324d4d1b7adb012d6`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `39` / recoverable `689c9696a7bc02c2bf183a03` / cause `orphan_user`
  original `Jueves 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-11T13:43:50.710000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `56` / recoverable `68afe7e265a2e69a26aca64a` / cause `orphan_user`
  original `Jueves 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-25T05:23:46.089000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838c24724d4d1b7adb01362`

- legacy user id: `6838c24724d4d1b7adb01362`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `38` / recoverable `689a93e9a7bc02c2bf0bd487` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-11T01:07:53.367000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `47` / recoverable `68a3c2936c2821996add6e84` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T00:17:23.653000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `101` / recoverable `68e7efcf83c46bbb4ec9f8f2` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T17:24:31.100000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `129` / recoverable `690d065487e38f36121de148` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-03T20:34:28.560000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838c39524d4d1b7adb01587`

- legacy user id: `6838c39524d4d1b7adb01587`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `41` / recoverable `689cec16a7bc02c2bf23f098` / cause `orphan_user`
  original `Jueves 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-11T19:48:38.017000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

- source `44` / recoverable `68a36cb56c2821996aca16d7` / cause `orphan_user`
  original `Lunes 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T18:11:01.796000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

- source `68` / recoverable `68b9d634bf7d3b69e9ddf254` / cause `orphan_user`
  original `Jueves 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T18:11:00.377000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

- source `71` / recoverable `68bf1c38816bba3a6e35e24f` / cause `orphan_user`
  original `Lunes 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T18:11:04.334000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838c52824d4d1b7adb01861`

- legacy user id: `6838c52824d4d1b7adb01861`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `53` / recoverable `68a65fc6c065187129cac4eb` / cause `orphan_user`
  original `Viernes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T23:52:38.567000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838c58a24d4d1b7adb01b08`

- legacy user id: `6838c58a24d4d1b7adb01b08`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `10` / recoverable `686ff92a437e48d868657cad` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-07T17:32:26.095000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838c88e24d4d1b7adb02452`

- legacy user id: `6838c88e24d4d1b7adb02452`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `21` / recoverable `688be22e8ced41d0c730b6e6` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-28T21:37:50.355000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838c9d324d4d1b7adb025f0`

- legacy user id: `6838c9d324d4d1b7adb025f0`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `1` / recoverable `6863c9332e6b6e0973a915ad` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-06-30T11:40:35.504000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `4` / recoverable `68666a031ce3537e43b15067` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-06-30T11:31:15.381000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838cde424d4d1b7adb02ecf`

- legacy user id: `6838cde424d4d1b7adb02ecf`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `144` / recoverable `691b06eac1d02e84fff46f3f` / cause `orphan_user`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T11:28:42.343000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838d48024d4d1b7adb03882`

- legacy user id: `6838d48024d4d1b7adb03882`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `104` / recoverable `68eed323653980b777dd24ee` / cause `orphan_user`
  original `Martes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-13T22:48:03.282000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `122` / recoverable `690132c7e57700f777337880` / cause `orphan_user`
  original `Martes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-27T21:16:55.233000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838d51d24d4d1b7adb03968`

- legacy user id: `6838d51d24d4d1b7adb03968`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `8` / recoverable `686d757e437e48d868574e40` / cause `orphan_user`
  original `Martes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-07T19:46:06.721000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `27` / recoverable `6890fc13584e00089ec52b76` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T18:29:39.128000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `106` / recoverable `68f1554c3d5cf39df131c520` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-13T20:27:56.518000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `223` / recoverable `69726903f61c580ccf09b264` / cause `orphan_user`
  original `Jueves 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T18:14:27.129000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838dcea24d4d1b7adb04cb2`

- legacy user id: `6838dcea24d4d1b7adb04cb2`
- current match status: `orphan_user`
- blocked rows in this bucket: **5**

- source `57` / recoverable `68b57361470911da156b85cf` / cause `orphan_user`
  original `Martes 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T10:20:17.697000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

- source `79` / recoverable `68c45c66a9d3e0b046e03a0d` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T17:46:14.484000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `140` / recoverable `69171236b9b11086f2d8ce5d` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T11:27:50.945000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `150` / recoverable `691e0459b727863d0d02a537` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T17:54:33.120000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `162` / recoverable `692589b4921b1937178b7e13` / cause `orphan_user`
  original `Martes 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T10:49:24.374000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838dde824d4d1b7adb04e38`

- legacy user id: `6838dde824d4d1b7adb04e38`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `91` / recoverable `68dc50e3f8d515529ded33d3` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-29T21:51:31.379000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838de0c24d4d1b7adb04eb7`

- legacy user id: `6838de0c24d4d1b7adb04eb7`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `151` / recoverable `691e04cdb727863d0d02ee75` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T17:56:29.539000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `163` / recoverable `692589fc921b1937178bd94d` / cause `orphan_user`
  original `Martes 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T10:50:36.068000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

- source `210` / recoverable `696149e5f61c580ccfad1bff` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T18:33:09.728000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838de6a24d4d1b7adb05054`

- legacy user id: `6838de6a24d4d1b7adb05054`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `36` / recoverable `68992f839fd0f2f9d833e036` / cause `orphan_user`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T23:47:15.533000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838e06724d4d1b7adb0526c`

- legacy user id: `6838e06724d4d1b7adb0526c`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `257` / recoverable `6998c418a777fa9be0652bc4` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T20:29:12.100000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `268` / recoverable `69a74a78a777fa9be0e5466b` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-02T20:54:16.318000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `392` / recoverable `6a03798e2d3685d816837dfe` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T19:03:42.196000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838eeac24d4d1b7adb06554`

- legacy user id: `6838eeac24d4d1b7adb06554`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `109` / recoverable `68f575c23d5cf39df149a138` / cause `orphan_user`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-13T23:35:30.378000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838f41f24d4d1b7adb06909`

- legacy user id: `6838f41f24d4d1b7adb06909`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `69` / recoverable `68b9fbd5816bba3a6e0df407` / cause `orphan_user`
  original `Jueves 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T20:51:33.454000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6838fab924d4d1b7adb06bb6`

- legacy user id: `6838fab924d4d1b7adb06bb6`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `74` / recoverable `68c1ac2b816bba3a6e6eef86` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T16:49:47.869000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `124` / recoverable `690408d0dfa89949cd42ce4f` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-27T00:54:40.001000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `190` / recoverable `693bea6ef61c580ccf1c29c3` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T10:11:58.302000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6839102724d4d1b7adb072c7`

- legacy user id: `6839102724d4d1b7adb072c7`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `19` / recoverable `688a4ff38ced41d0c707523c` / cause `orphan_user`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-28T17:01:39.546000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `20` / recoverable `688a500c8ced41d0c707665b` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-28T17:02:04.655000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `46` / recoverable `68a397ab6c2821996ad6dc13` / cause `orphan_user`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T21:14:19.268000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `258` / recoverable `699c446aa777fa9be06edf64` / cause `orphan_user`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-23T12:13:30.903000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683924ca24d4d1b7adb076bd`

- legacy user id: `683924ca24d4d1b7adb076bd`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `3` / recoverable `68642b6e2e6b6e0973adf9e3` / cause `orphan_user`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-06-30T18:39:42.174000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `11` / recoverable `68727553437e48d8687945c5` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-07T14:46:43.442000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `49` / recoverable `68a4cc5d6c2821996ae65b5e` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T19:11:25+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `63` / recoverable `68b8f48bbf7d3b69e9d110d7` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T02:08:11.981000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6839abb924d4d1b7adb08def`

- legacy user id: `6839abb924d4d1b7adb08def`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `108` / recoverable `68f220873d5cf39df1384f67` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-13T10:55:03.675000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `172` / recoverable `6928fc4bf9567aa86a6e9c08` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T01:35:07.512000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6839b54224d4d1b7adb09c20`

- legacy user id: `6839b54224d4d1b7adb09c20`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `28` / recoverable `6891f4d2a3c918c12b4daba1` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T12:10:58.940000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `43` / recoverable `68a36a3c6c2821996ac8fad5` / cause `orphan_user`
  original `Lunes 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T18:00:28.225000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6839e93d24d4d1b7adb0b781`

- legacy user id: `6839e93d24d4d1b7adb0b781`
- current match status: `orphan_user`
- blocked rows in this bucket: **6**

- source `200` / recoverable `69447462f61c580ccf49fe56` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-15T21:38:42.424000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `209` / recoverable `695ffdb4f61c580ccfa9629d` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T18:55:48.115000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `229` / recoverable `697bc16ff61c580ccf3feb79` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-26T20:22:07.925000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `238` / recoverable `69850086f61c580ccf8260ea` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T20:41:42.771000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `264` / recoverable `69a0b23ca777fa9be0aebfcd` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-23T20:51:08.157000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `274` / recoverable `69a9f82fa777fa9be008c767` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-02T21:39:59.663000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6839fe4424d4d1b7adb0be2b`

- legacy user id: `6839fe4424d4d1b7adb0be2b`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `25` / recoverable `688d1fc6584e00089e9c530f` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-28T20:12:54.385000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `34` / recoverable `689656e8418f2e9a6b6247c3` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T19:58:32.412000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683a043924d4d1b7adb0c442`

- legacy user id: `683a043924d4d1b7adb0c442`
- current match status: `orphan_user`
- blocked rows in this bucket: **5**

- source `170` / recoverable `69274d63f9567aa86a440229` / cause `orphan_user`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T18:56:35.044000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `180` / recoverable `693221f49b8341009fcc4787` / cause `orphan_user`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T00:06:12.991000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `216` / recoverable `696d96d8f61c580ccfed3c08` / cause `orphan_user`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T02:28:40.851000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `234` / recoverable `69839740f61c580ccf705fd7` / cause `orphan_user`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T19:00:16.139000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `263` / recoverable `699f2fdda777fa9be0a2c2de` / cause `orphan_user`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-23T17:22:37.317000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683a058e24d4d1b7adb0c693`

- legacy user id: `683a058e24d4d1b7adb0c693`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `55` / recoverable `68ac415004fd43e733af7272` / cause `orphan_user`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-25T10:56:16.679000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683a074724d4d1b7adb0c82b`

- legacy user id: `683a074724d4d1b7adb0c82b`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `92` / recoverable `68dd1e8bf8d515529df6b5d9` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-29T12:28:59.956000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `158` / recoverable `69205bcd0080ca3e3c0c9ebe` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T12:32:13.413000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `226` / recoverable `6976e13cf61c580ccf12fd28` / cause `orphan_user`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-26T03:36:28.895000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `246` / recoverable `698cd4a8aea2ece5ecc2f112` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-09T19:12:40.487000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683a08e224d4d1b7adb0c9c7`

- legacy user id: `683a08e224d4d1b7adb0c9c7`
- current match status: `orphan_user`
- blocked rows in this bucket: **9**

- source `9` / recoverable `686fa676437e48d86860d498` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-07T11:39:34.693000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `31` / recoverable `689489a2418f2e9a6b4dcd8c` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T11:10:26.423000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `54` / recoverable `68ab0b4704fd43e733a66074` / cause `orphan_user`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T12:53:27.713000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `61` / recoverable `68b8cbd1bf7d3b69e9cfb9af` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T23:14:25.567000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `75` / recoverable `68c2aaa0816bba3a6e7eaf02` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T10:55:28.319000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `95` / recoverable `68e47fd183c46bbb4eaacf63` / cause `orphan_user`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T02:49:53.422000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `136` / recoverable `69128ade18c10abc35de07fe` / cause `orphan_user`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T01:01:18.193000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `193` / recoverable `6940b5d0f61c580ccf36371b` / cause `orphan_user`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-15T01:28:48.594000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `197` / recoverable `69421a3ef61c580ccf3f17af` / cause `orphan_user`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-15T02:49:34.840000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683a091924d4d1b7adb0cb65`

- legacy user id: `683a091924d4d1b7adb0cb65`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `93` / recoverable `68e291bd83c46bbb4e90fd4d` / cause `orphan_user`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-29T15:41:49.701000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `102` / recoverable `68ec119b83c46bbb4ed4e30d` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T20:37:47.536000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `149` / recoverable `691c7827c06af9f8f6d5b716` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T13:44:07.380000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `154` / recoverable `691f69ed89d58e67e7136a1a` / cause `orphan_user`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T19:20:13.220000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683a260724d4d1b7adb0d39b`

- legacy user id: `683a260724d4d1b7adb0d39b`
- current match status: `orphan_user`
- blocked rows in this bucket: **15**

- source `24` / recoverable `688cf470584e00089e994873` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-28T17:08:00.730000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `84` / recoverable `68cc7250c11c04213f558d4d` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-15T20:57:52.398000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `100` / recoverable `68e6cee083c46bbb4ebb79f9` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T20:51:44.637000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `125` / recoverable `69052a32dfa89949cd711992` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-27T21:29:22.691000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `168` / recoverable `6927324765b641b09e3313dd` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T17:00:55.916000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `169` / recoverable `6927325b65b641b09e33346c` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T17:01:15.209000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `181` / recoverable `69333d45f61c580ccfded331` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T20:15:01.206000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `198` / recoverable `6943246bf61c580ccf44a549` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-15T21:45:15.359000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `212` / recoverable `69616d23f61c580ccfaf4b49` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T21:03:31.600000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `222` / recoverable `69714fd9f61c580ccf06a108` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T22:14:49.872000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `225` / recoverable `6973e97af61c580ccf1128a0` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T21:34:50.292000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `239` / recoverable `698652dff61c580ccf87be17` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T20:45:19.572000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `251` / recoverable `69961871a777fa9be052a97a` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T19:52:17.512000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `279` / recoverable `69b1a891a777fa9be0473399` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T17:38:25.212000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `288` / recoverable `69b45b90a33212cb50ff1e5c` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T18:46:40.033000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683a38c524d4d1b7adb0d622`

- legacy user id: `683a38c524d4d1b7adb0d622`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `17` / recoverable `6883a8366c3009473a1290a4` / cause `orphan_user`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-21T15:52:22.987000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683d889124d4d1b7adb13adf`

- legacy user id: `683d889124d4d1b7adb13adf`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `14` / recoverable `6876c4df437e48d8689ca16a` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-14T21:15:11.001000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683d92ba24d4d1b7adb14851`

- legacy user id: `683d92ba24d4d1b7adb14851`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `110` / recoverable `68f597b63d5cf39df14be82a` / cause `orphan_user`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-20T02:00:22.051000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `111` / recoverable `68f597eb3d5cf39df14c0e02` / cause `orphan_user`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-20T02:01:15.390000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683d93d824d4d1b7adb14a47`

- legacy user id: `683d93d824d4d1b7adb14a47`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `16` / recoverable `687fbd0a0087715e6f9304cc` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-21T16:32:10.863000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683db77324d4d1b7adb15fd9`

- legacy user id: `683db77324d4d1b7adb15fd9`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `83` / recoverable `68cb1acac11c04213f427442` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-15T20:32:10.643000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683e290a54c3c5d82dd83602`

- legacy user id: `683e290a54c3c5d82dd83602`
- current match status: `orphan_user`
- blocked rows in this bucket: **5**

- source `58` / recoverable `68b619f12ad8dffefd7e496f` / cause `orphan_user`
  original `Lunes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T22:10:57.531000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `94` / recoverable `68e443f383c46bbb4ea8cbf8` / cause `orphan_user`
  original `Lunes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T22:34:27.706000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `119` / recoverable `68ffdc09e57700f7772452f0` / cause `orphan_user`
  original `Lunes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-27T20:54:33.619000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `175` / recoverable `6930b480f97ed95f72ed75ed` / cause `orphan_user`
  original `Lunes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T22:06:56.416000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `183` / recoverable `693705d5f61c580ccfe364e1` / cause `orphan_user`
  original `Lunes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T17:07:33.018000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `683ef3cd54c3c5d82dd8e187`

- legacy user id: `683ef3cd54c3c5d82dd8e187`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `7` / recoverable `686c6d7e437e48d8684d8cea` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-07T00:59:42.993000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `13` / recoverable `687523f4437e48d8688e3727` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-14T15:36:20.066000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6840898e33830ca09bed4724`

- legacy user id: `6840898e33830ca09bed4724`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `5` / recoverable `686a8bf7437e48d8681cfa47` / cause `orphan_user`
  original `Lunes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-06-30T14:45:11.219000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `6` / recoverable `686a8cde437e48d8681d2f2c` / cause `orphan_user`
  original `Viernes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-06-30T14:49:02.232000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6841f3dea48252fc66414ade`

- legacy user id: `6841f3dea48252fc66414ade`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `15` / recoverable `68798d5b45779e699660de93` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-14T23:55:07.957000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68483774111d7b411318bf28`

- legacy user id: `68483774111d7b411318bf28`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `40` / recoverable `689ca99aa7bc02c2bf210eed` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `Martes 20:00` / recovered `false`
  cancelledWeek `2025-08-11T15:04:58.943000+00:00` / recoveryDate `2025-08-19T22:45:55.463000+00:00` / possible sections `cadillac | reformer_abajo`
  secondary blockers: inconsistent_state, ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `117` / recoverable `68fe544be57700f77716c683` / cause `orphan_user`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-20T17:03:07.770000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `132` / recoverable `6910b41fd1266371eaeb2628` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-03T15:32:47.046000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `133` / recoverable `6910b480d1266371eaeb48e0` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-03T15:34:24.338000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `684a09d7111d7b4113190d02`

- legacy user id: `684a09d7111d7b4113190d02`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `30` / recoverable `689350a9418f2e9a6b2d233d` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T12:55:05.584000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `37` / recoverable `6899d9219fd0f2f9d83975df` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-11T11:50:57.338000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `113` / recoverable `68f7b99f3d5cf39df1685d46` / cause `orphan_user`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-20T16:49:35.076000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `684d99573fd821bc9584a364`

- legacy user id: `684d99573fd821bc9584a364`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `463` / recoverable `6a1637f81021c0c1fbdaf02c` / cause `orphan_user`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T00:16:56.190000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68593cc6fc3f31a1c1510199`

- legacy user id: `68593cc6fc3f31a1c1510199`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `128` / recoverable `690ce46b87e38f3612194544` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-03T18:09:47.564000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `185` / recoverable `6937f088f61c580ccfec30ee` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T09:48:56.028000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68596128fc3f31a1c1512aed`

- legacy user id: `68596128fc3f31a1c1512aed`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `32` / recoverable `6894ad0f418f2e9a6b4e71df` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T13:41:35.276000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `685ff53731a3dc27dbc0bc1b`

- legacy user id: `685ff53731a3dc27dbc0bc1b`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `312` / recoverable `69cd31dee85c03079de06a33` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T14:55:26.600000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `344` / recoverable `69e5abd8e85c03079de51730` / cause `orphan_user`
  original `Lunes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-20T04:30:16.895000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `360` / recoverable `69eecc0ee85c03079de693a5` / cause `orphan_user`
  original `Lunes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-27T02:38:06.749000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6860102831a3dc27dbc0cbe4`

- legacy user id: `6860102831a3dc27dbc0cbe4`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `73` / recoverable `68c08670816bba3a6e4fb259` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T19:56:32.030000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68601af731a3dc27dbc0cfea`

- legacy user id: `68601af731a3dc27dbc0cfea`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `60` / recoverable `68b7419dcc554e20f1188e27` / cause `orphan_user`
  original `Martes 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T19:12:29.490000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68615acf31a3dc27dbc0e804`

- legacy user id: `68615acf31a3dc27dbc0e804`
- current match status: `orphan_user`
- blocked rows in this bucket: **17**

- source `22` / recoverable `688cb064584e00089e8d39ef` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-28T12:17:40.464000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `33` / recoverable `6894ff54418f2e9a6b54ccc4` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T19:32:36.539000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `78` / recoverable `68c40194816bba3a6e8e72a3` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T11:18:44.612000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `81` / recoverable `68c8d3a642a86feb875f9447` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-15T03:04:06.641000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `96` / recoverable `68e497cc83c46bbb4eabd963` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T04:32:12.535000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `107` / recoverable `68f1a27a3d5cf39df135e22f` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-13T01:57:14.377000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `139` / recoverable `69165fd2b9b11086f2d7297a` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T22:46:42.874000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `147` / recoverable `691c4761c06af9f8f6ce7c0c` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T10:16:01.020000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `148` / recoverable `691c4779c06af9f8f6ce8eca` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T10:16:25.267000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `174` / recoverable `692eb56f2023ebfc89aa50bf` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T09:46:23.176000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `179` / recoverable `6931fcb09b8341009fcb777d` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T21:27:12.851000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `208` / recoverable `695faf9ff61c580ccfa810c0` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T13:22:39.032000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `221` / recoverable `696f350cf61c580ccff78f53` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T07:55:56.534000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `376` / recoverable `69fd943c27e24d7c86c44188` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T07:43:56.487000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `407` / recoverable `6a0a54671021c0c1fbd81d6f` / cause `orphan_user`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T23:51:03.049000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `430` / recoverable `6a0fc70d1021c0c1fbd98a53` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T03:01:33.012000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `431` / recoverable `6a0fc7231021c0c1fbd98b78` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T03:01:55.008000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6863d3cc2e6b6e0973a9be0d`

- legacy user id: `6863d3cc2e6b6e0973a9be0d`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `143` / recoverable `691a1160c1d02e84ffee0835` / cause `orphan_user`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T18:01:04.647000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `686717c21ce3537e43ba2d11`

- legacy user id: `686717c21ce3537e43ba2d11`
- current match status: `orphan_user`
- blocked rows in this bucket: **6**

- source `196` / recoverable `694157faf61c580ccf3a8a5f` / cause `orphan_user`
  original `Martes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-15T13:00:42.249000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `205` / recoverable `695d08c6f61c580ccf91888d` / cause `orphan_user`
  original `Martes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T13:06:14.550000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `244` / recoverable `698b253db26892186fe2c150` / cause `orphan_user`
  original `Martes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-09T12:31:57.504000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `277` / recoverable `69b01546a777fa9be036805e` / cause `orphan_user`
  original `Martes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T12:57:42.128000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `287` / recoverable `69b34a85a777fa9be05299e8` / cause `orphan_user`
  original `Jueves 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T23:21:41.854000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `328` / recoverable `69d7b53ce85c03079de2f2eb` / cause `orphan_user`
  original `Jueves 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T14:18:36.300000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `686bc141437e48d8682ec38c`

- legacy user id: `686bc141437e48d8682ec38c`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `62` / recoverable `68b8dcf6bf7d3b69e9d04352` / cause `orphan_user`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T00:27:34.053000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `686d1f62437e48d86851e16d`

- legacy user id: `686d1f62437e48d86851e16d`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `64` / recoverable `68b9614fbf7d3b69e9d3b570` / cause `orphan_user`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T09:52:15.483000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `686d42d4437e48d86853f9d0`

- legacy user id: `686d42d4437e48d86853f9d0`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `12` / recoverable `6875001e437e48d86883de05` / cause `orphan_user`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-14T13:03:26.543000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68767878437e48d868985f2a`

- legacy user id: `68767878437e48d868985f2a`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `65` / recoverable `68b9777fbf7d3b69e9d62aa7` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T11:26:55.222000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `121` / recoverable `6900a581e57700f7772cd922` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-27T11:14:09.606000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `157` / recoverable `6920483889d58e67e717c9ad` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T11:08:40.515000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `189` / recoverable `693b78c4f61c580ccf1bd035` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T02:07:00.192000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6876d8db437e48d8689de43b`

- legacy user id: `6876d8db437e48d8689de43b`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `182` / recoverable `6934295ef61c580ccfdf95ef` / cause `orphan_user`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T13:02:22.707000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `687c307145779e699669991d`

- legacy user id: `687c307145779e699669991d`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `18` / recoverable `6888febd6c3009473a5090fc` / cause `orphan_user`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-28T17:02:53.456000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `687e828e45779e69967b7f57`

- legacy user id: `687e828e45779e69967b7f57`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `153` / recoverable `691f690b89d58e67e713338d` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T19:16:27.154000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `688a2aa56c3009473a6492ef`

- legacy user id: `688a2aa56c3009473a6492ef`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `161` / recoverable `69257e1d921b1937178a0b0e` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T09:59:57.615000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `688aa1458ced41d0c70da9b2`

- legacy user id: `688aa1458ced41d0c70da9b2`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `99` / recoverable `68e6aa6c83c46bbb4eb967bf` / cause `orphan_user`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T18:16:12.442000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `145` / recoverable `691b5f76c1d02e84fffcf779` / cause `orphan_user`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T17:46:30.435000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `688d3c45584e00089ea2d298`

- legacy user id: `688d3c45584e00089ea2d298`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `206` / recoverable `695e6db0f61c580ccf985728` / cause `orphan_user`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T14:29:04.564000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `688f73ec584e00089eaabec0`

- legacy user id: `688f73ec584e00089eaabec0`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `89` / recoverable `68d7d98ac11c04213fc18dad` / cause `orphan_user`
  original `Jueves 16:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-22T12:33:14.023000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `688fdf4f584e00089eb07dc4`

- legacy user id: `688fdf4f584e00089eb07dc4`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `88` / recoverable `68d5b5f9c11c04213fa1e1ae` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-22T21:36:57.323000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `115` / recoverable `68faa1ec3d5cf39df17fde11` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-20T21:45:16.828000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68914260a3c918c12b429cd5`

- legacy user id: `68914260a3c918c12b429cd5`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `80` / recoverable `68c8578f42a86feb874accb6` / cause `orphan_user`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-15T18:14:39.495000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6892a319418f2e9a6b283f92`

- legacy user id: `6892a319418f2e9a6b283f92`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `45` / recoverable `68a38d3f6c2821996ad15838` / cause `orphan_user`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T20:29:51.090000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `48` / recoverable `68a4a3dc6c2821996ae5626c` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T16:18:36.606000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6893bd76418f2e9a6b4178b9`

- legacy user id: `6893bd76418f2e9a6b4178b9`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `76` / recoverable `68c327e2816bba3a6e8668b2` / cause `orphan_user`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T19:49:54.103000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `689cabb1a7bc02c2bf2130b4`

- legacy user id: `689cabb1a7bc02c2bf2130b4`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `72` / recoverable `68c04694816bba3a6e4aac75` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T15:24:04.878000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `689f7363a7bc02c2bf5605c4`

- legacy user id: `689f7363a7bc02c2bf5605c4`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `67` / recoverable `68b9b2fcbf7d3b69e9dcf16e` / cause `orphan_user`
  original `Jueves 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T15:40:44.013000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `178` / recoverable `6931f4869b8341009fca84e5` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T20:52:22.739000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68a4e2d9cabfea15ebf64934`

- legacy user id: `68a4e2d9cabfea15ebf64934`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `50` / recoverable `68a4e300cabfea15ebf68efd` / cause `orphan_user`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T20:48:00.099000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `51` / recoverable `68a4e631cabfea15eb0d6105` / cause `orphan_user`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-18T21:01:37.806000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68a71fccc065187129dc0cf7`

- legacy user id: `68a71fccc065187129dc0cf7`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `131` / recoverable `690e4958d1266371eae570b5` / cause `orphan_user`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-03T19:32:40.794000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `141` / recoverable `6917837ea5faeea25d9c3fc6` / cause `orphan_user`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T19:31:10.142000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `142` / recoverable `6919d766c1d02e84ffed50ce` / cause `orphan_user`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T13:53:42.354000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68adc28f04fd43e733cc0449`

- legacy user id: `68adc28f04fd43e733cc0449`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `123` / recoverable `6903393cdfa89949cd3f5a1f` / cause `orphan_user`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-27T10:09:00.026000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `176` / recoverable `6930e56af97ed95f72efb51d` / cause `orphan_user`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T01:35:38.315000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `184` / recoverable `69373ffff61c580ccfe56bd8` / cause `orphan_user`
  original `Lunes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T21:15:43.052000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `215` / recoverable `6968d6b4f61c580ccfe0f045` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-12T11:59:48.682000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68af695365a2e69a26a07980`

- legacy user id: `68af695365a2e69a26a07980`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `85` / recoverable `68d13f01c11c04213f6c339b` / cause `orphan_user`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-22T12:20:17.604000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68b1c81465a2e69a26c4938e`

- legacy user id: `68b1c81465a2e69a26c4938e`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `114` / recoverable `68fa2b163d5cf39df177936a` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-20T13:18:14.175000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `118` / recoverable `68ff97e8e57700f7771d587c` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-27T16:03:52.812000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68b201e8d86823f0b38a4934`

- legacy user id: `68b201e8d86823f0b38a4934`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `66` / recoverable `68b983b8bf7d3b69e9d6805e` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T12:19:04.934000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68b20e52d86823f0b38ff906`

- legacy user id: `68b20e52d86823f0b38ff906`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `135` / recoverable `69124b0918c10abc35d8c13b` / cause `orphan_user`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T20:28:57.994000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68b8511cbf7d3b69e9b969e2`

- legacy user id: `68b8511cbf7d3b69e9b969e2`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `77` / recoverable `68c3f52c816bba3a6e8dedcb` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-08T10:25:48.687000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68b99941bf7d3b69e9db87a7`

- legacy user id: `68b99941bf7d3b69e9db87a7`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `70` / recoverable `68bae9e2816bba3a6e148f97` / cause `orphan_user`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-01T13:47:14.356000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68bef590816bba3a6e3329bd`

- legacy user id: `68bef590816bba3a6e3329bd`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `105` / recoverable `68ef9c1e653980b777e44003` / cause `orphan_user`
  original `Viernes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-13T13:05:34.384000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68cb235fc11c04213f42c6aa`

- legacy user id: `68cb235fc11c04213f42c6aa`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `424` / recoverable `6a0eeac91021c0c1fbd93b9f` / cause `orphan_user`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T11:21:45.874000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `438` / recoverable `6a14105d1021c0c1fbd9ce8f` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T09:03:25.250000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `439` / recoverable `6a1410791021c0c1fbd9cf93` / cause `orphan_user`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T09:03:53.507000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68da6e58ff8230f507f70334`

- legacy user id: `68da6e58ff8230f507f70334`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `98` / recoverable `68e564b283c46bbb4eb0e1fb` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-06T19:06:26.772000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `164` / recoverable `6925fd1c921b19371795126a` / cause `orphan_user`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T19:01:48.509000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `68ed166183c46bbb4edc2dfa`

- legacy user id: `68ed166183c46bbb4edc2dfa`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `152` / recoverable `691f666289d58e67e70fc7c6` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T19:05:06.563000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6904be1ddfa89949cd4b8335`

- legacy user id: `6904be1ddfa89949cd4b8335`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `171` / recoverable `6927a5f1f9567aa86a47fa5f` / cause `orphan_user`
  original `Viernes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T01:14:25.230000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6908b39c123d0671aed6e48b`

- legacy user id: `6908b39c123d0671aed6e48b`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `130` / recoverable `690de966d1266371eada421e` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-03T12:43:18.521000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6908ce33123d0671aee2dfc8`

- legacy user id: `6908ce33123d0671aee2dfc8`
- current match status: `orphan_user`
- blocked rows in this bucket: **3**

- source `146` / recoverable `691b7f97c1d02e84ffff5db3` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T20:03:35.711000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `156` / recoverable `691fb22d89d58e67e717a089` / cause `orphan_user`
  original `Viernes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T00:28:29.682000+00:00` / recoveryDate `-` / possible sections `-`
  secondary blockers: missing_section_mapping
  detail: No current student matches this legacy_user_id.

- source `160` / recoverable `692521bb921b193717884e0d` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T03:25:47.483000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6911d1f918c10abc35cc3de9`

- legacy user id: `6911d1f918c10abc35cc3de9`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `173` / recoverable `692df2372023ebfc89a3fd44` / cause `orphan_user`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T19:53:27.497000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6915ccdbb9b11086f2cd9b69`

- legacy user id: `6915ccdbb9b11086f2cd9b69`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `138` / recoverable `6915f977b9b11086f2ce72e2` / cause `orphan_user`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T15:29:59.918000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6915fb7ab9b11086f2ce8dca`

- legacy user id: `6915fb7ab9b11086f2ce8dca`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `177` / recoverable `693150bb9b8341009fc5ea0d` / cause `orphan_user`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-01T09:13:31.219000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69164402b9b11086f2d56ba9`

- legacy user id: `69164402b9b11086f2d56ba9`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `155` / recoverable `691fb16289d58e67e716ee3d` / cause `orphan_user`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-17T00:25:06.621000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `165` / recoverable `69260123921b193717973526` / cause `orphan_user`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T19:18:59.247000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `691f262289d58e67e70ace15`

- legacy user id: `691f262289d58e67e70ace15`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `247` / recoverable `69930f3da777fa9be0429dcb` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T12:36:13.182000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `259` / recoverable `699c460ba777fa9be06f703b` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-23T12:20:27.769000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `692607cb921b1937179c367d`

- legacy user id: `692607cb921b1937179c367d`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `243` / recoverable `698a8ec3b26892186fdfc2c2` / cause `orphan_user`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-09T01:49:55.110000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `255` / recoverable `69989d51a777fa9be063a667` / cause `orphan_user`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T17:43:45.022000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6928707df9567aa86a593e07`

- legacy user id: `6928707df9567aa86a593e07`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `202` / recoverable `694ac098f61c580ccf651e9b` / cause `orphan_user`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-22T16:17:28.220000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `692a2e72f9567aa86a7bd999`

- legacy user id: `692a2e72f9567aa86a7bd999`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `186` / recoverable `6938a28ef61c580ccf00346a` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T22:28:30.333000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `692e111b2023ebfc89a60412`

- legacy user id: `692e111b2023ebfc89a60412`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `302` / recoverable `69c6f8dc2a1c963ea9ace8b8` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-23T21:38:36.345000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `692ee9f72023ebfc89b07950`

- legacy user id: `692ee9f72023ebfc89b07950`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `191` / recoverable `693c42a1f61c580ccf200f2d` / cause `orphan_user`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T16:28:17.391000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `693abcf4f61c580ccf174bf3`

- legacy user id: `693abcf4f61c580ccf174bf3`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `211` / recoverable `69614a2af61c580ccfad47d0` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T18:34:18.899000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `256` / recoverable `6998b92ea777fa9be0644208` / cause `orphan_user`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T19:42:38.549000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69414a61f61c580ccf392ee0`

- legacy user id: `69414a61f61c580ccf392ee0`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `194` / recoverable `6941506ff61c580ccf39ea60` / cause `orphan_user`
  original `Martes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-15T12:28:31.810000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `195` / recoverable `694150d0f61c580ccf3a3fcc` / cause `orphan_user`
  original `Jueves 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-15T12:30:08.783000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6949b572f61c580ccf5ce0e9`

- legacy user id: `6949b572f61c580ccf5ce0e9`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `324` / recoverable `69d6b070e85c03079de2b240` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T19:45:52.654000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `695c2918f61c580ccf8df838`

- legacy user id: `695c2918f61c580ccf8df838`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `327` / recoverable `69d6dea2e85c03079de2c557` / cause `orphan_user`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T23:02:58.174000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `422` / recoverable `6a0e45131021c0c1fbd92c53` / cause `orphan_user`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T23:34:43.998000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `695ea094f61c580ccf99ba4b`

- legacy user id: `695ea094f61c580ccf99ba4b`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `220` / recoverable `696ec648f61c580ccff683c5` / cause `orphan_user`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T00:03:20.119000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `695f965ef61c580ccfa72dd4`

- legacy user id: `695f965ef61c580ccfa72dd4`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `235` / recoverable `6983cc73f61c580ccf752a0c` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T22:47:15.608000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69653a81f61c580ccfc1c4fd`

- legacy user id: `69653a81f61c580ccfc1c4fd`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `249` / recoverable `6994557ca777fa9be043353a` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T11:48:12.901000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `260` / recoverable `699c4b55a777fa9be0718c43` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-23T12:43:01.710000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69655a8af61c580ccfc32ba4`

- legacy user id: `69655a8af61c580ccfc32ba4`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `217` / recoverable `696e5643f61c580ccff18dfd` / cause `orphan_user`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T16:05:23.332000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `218` / recoverable `696e565ff61c580ccff19f3f` / cause `orphan_user`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T16:05:51.951000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69663652f61c580ccfca2834`

- legacy user id: `69663652f61c580ccfca2834`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `228` / recoverable `69798233f61c580ccf245e60` / cause `orphan_user`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-26T03:27:47.536000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `697b6295f61c580ccf3de0ae`

- legacy user id: `697b6295f61c580ccf3de0ae`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `262` / recoverable `699e21fba777fa9be09644e9` / cause `orphan_user`
  original `Martes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-23T22:11:07.782000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `697ba389f61c580ccf3f091e`

- legacy user id: `697ba389f61c580ccf3f091e`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `237` / recoverable `6984f350f61c580ccf8174ac` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T19:45:20.646000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `355` / recoverable `69ea73fbe85c03079de5ea87` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-20T19:33:15.437000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `458` / recoverable `6a15def81021c0c1fbdac76d` / cause `orphan_user`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T17:57:12.630000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `474` / recoverable `6a1891691021c0c1fbdbdde5` / cause `orphan_user`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T19:03:05.491000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `697bd3b4f61c580ccf410685`

- legacy user id: `697bd3b4f61c580ccf410685`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `240` / recoverable `6987c4f5f61c580ccf882894` / cause `orphan_user`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T23:04:21.781000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `241` / recoverable `6987c50bf61c580ccf883fc8` / cause `orphan_user`
  original `Viernes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T23:04:43.151000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `697bd44ef61c580ccf41068c`

- legacy user id: `697bd44ef61c580ccf41068c`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `250` / recoverable `6994d1dba777fa9be04451ec` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T20:38:51.412000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `261` / recoverable `699d1cf4a777fa9be08b3f7b` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-23T03:37:24.112000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `697cd9b6f61c580ccf4d97aa`

- legacy user id: `697cd9b6f61c580ccf4d97aa`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `253` / recoverable `6996d3a8a777fa9be057d4d5` / cause `orphan_user`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T09:11:04.458000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `254` / recoverable `6996d3bba777fa9be057ea27` / cause `orphan_user`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T09:11:23.354000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6980f60ef61c580ccf5f058a`

- legacy user id: `6980f60ef61c580ccf5f058a`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `245` / recoverable `698c6508aea2ece5ecc09981` / cause `orphan_user`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-09T11:16:24.375000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6983baecf61c580ccf727d26`

- legacy user id: `6983baecf61c580ccf727d26`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `306` / recoverable `69cc1d69e85c03079de007f2` / cause `orphan_user`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T19:15:53.040000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `307` / recoverable `69cc1da5e85c03079de008e3` / cause `orphan_user`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T19:16:53.458000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69a2e51ba777fa9be0c535ee`

- legacy user id: `69a2e51ba777fa9be0c535ee`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `446` / recoverable `6a1471821021c0c1fbd9f13d` / cause `orphan_user`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T15:57:54.043000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69a3519da777fa9be0c75edb`

- legacy user id: `69a3519da777fa9be0c75edb`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `404` / recoverable `6a0631a51021c0c1fbd7ab8f` / cause `orphan_user`
  original `Jueves 20:00` -> assigned `Viernes 19:00` / recovered `true`
  cancelledWeek `2026-05-11T20:33:41.003000+00:00` / recoveryDate `2026-05-29T00:00:00+00:00` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69a586e3a777fa9be0d54209`

- legacy user id: `69a586e3a777fa9be0d54209`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `282` / recoverable `69b1f2b7a777fa9be04bcc01` / cause `orphan_user`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T22:54:47.558000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69cbf798e85c03079ddffee5`

- legacy user id: `69cbf798e85c03079ddffee5`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `380` / recoverable `6a01c0672d3685d81682ec6a` / cause `orphan_user`
  original `Lunes 10:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T11:41:27.930000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69cd0102e85c03079de0496d`

- legacy user id: `69cd0102e85c03079de0496d`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `349` / recoverable `69e77d46e85c03079de58015` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `Martes 10:00` / recovered `true`
  cancelledWeek `2026-04-20T13:36:06.546000+00:00` / recoveryDate `2026-05-26T00:00:00+00:00` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `432` / recoverable `6a107c9f1021c0c1fbd9a335` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `Jueves 10:00` / recovered `true`
  cancelledWeek `2026-05-18T15:56:15.247000+00:00` / recoveryDate `2026-05-28T00:00:00+00:00` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `448` / recoverable `6a15077c1021c0c1fbda652d` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T02:37:48.135000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `508` / recoverable `6a22a4e11021c0c1fbde2a95` / cause `orphan_user`
  original `Viernes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T10:28:49.522000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69e02102e85c03079de41b28`

- legacy user id: `69e02102e85c03079de41b28`
- current match status: `orphan_user`
- blocked rows in this bucket: **4**

- source `373` / recoverable `69fcba4827e24d7c86c41be2` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T16:14:00.185000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `389` / recoverable `6a0296e32d3685d816835519` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T02:56:35.453000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `425` / recoverable `6a0effad1021c0c1fbd9458f` / cause `orphan_user`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T12:50:53.363000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `473` / recoverable `6a187f341021c0c1fbdbc317` / cause `orphan_user`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T17:45:24.494000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69ef5794e85c03079de6af56`

- legacy user id: `69ef5794e85c03079de6af56`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `442` / recoverable `6a144fc41021c0c1fbd9d995` / cause `orphan_user`
  original `Lunes 08:00` -> assigned `Jueves 07:00` / recovered `true`
  cancelledWeek `2026-05-25T13:33:56.852000+00:00` / recoveryDate `2026-05-28T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69f11887e85c03079de72292`

- legacy user id: `69f11887e85c03079de72292`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `363` / recoverable `69f11905e85c03079de72e1c` / cause `orphan_user`
  original `Miércoles 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-27T20:31:01.879000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69f118afe85c03079de72665`

- legacy user id: `69f118afe85c03079de72665`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `369` / recoverable `69f9f3c86e43b612a8d6930d` / cause `orphan_user`
  original `Viernes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T13:42:32.007000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

- source `441` / recoverable `6a1439af1021c0c1fbd9d399` / cause `orphan_user`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T11:59:43.895000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `69fe699d27e24d7c86c47b53`

- legacy user id: `69fe699d27e24d7c86c47b53`
- current match status: `orphan_user`
- blocked rows in this bucket: **2**

- source `378` / recoverable `69fe6aa927e24d7c86c48675` / cause `orphan_user`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T22:58:49.545000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

- source `379` / recoverable `69fe6b4227e24d7c86c4906d` / cause `orphan_user`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T23:01:22.849000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: No current student matches this legacy_user_id.

### Name unavailable - `6a05ef111021c0c1fbd79755`

- legacy user id: `6a05ef111021c0c1fbd79755`
- current match status: `orphan_user`
- blocked rows in this bucket: **1**

- source `444` / recoverable `6a1459be1021c0c1fbd9e8d7` / cause `orphan_user`
  original `Lunes 20:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T14:16:30.325000+00:00` / recoveryDate `-` / possible sections `reformer_abajo`
  detail: No current student matches this legacy_user_id.

### agustina comelli - `carluccifranco9@gmail.com`

- legacy user id: `6984a90ff61c580ccf7e7c03`
- current match status: `matched`
- current app user: `carluccifranco9@gmail.com` / id `57`
- blocked rows in this bucket: **1**

- source `595` / recoverable `6a3940b41021c0c1fbe34d20` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T14:03:32.181000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### agustina jurjo - `agusjurjo@gmail.com`

- legacy user id: `6839e89a24d4d1b7adb0b551`
- current match status: `matched`
- current app user: `agusjurjo@gmail.com` / id `18`
- blocked rows in this bucket: **6**

- source `137` / recoverable `691382e6e922794f46491df0` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-10T18:39:34.257000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `267` / recoverable `69a5dfb3a777fa9be0d975e6` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-02T19:06:27.896000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `303` / recoverable `69c917c92a1c963ea9ad24e4` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-23T12:15:05.596000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `323` / recoverable `69d40e13e85c03079de0e43b` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T19:48:35.077000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `391` / recoverable `6a033af22d3685d81683721f` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T14:36:34.321000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `533` / recoverable `6a29d4411021c0c1fbdff611` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T21:16:49.079000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### agustina quiroga - `quirogaagustina109@gmail.com`

- legacy user id: `69ea8f6be85c03079de611fd`
- current match status: `matched`
- current app user: `quirogaagustina109@gmail.com` / id `91`
- blocked rows in this bucket: **5**

- source `366` / recoverable `69f8731b6e43b612a8d5a0f3` / cause `ambiguous_section`
  original `Lunes 19:00` -> assigned `Lunes 20:00` / recovered `true`
  cancelledWeek `2026-05-04T10:21:15.993000+00:00` / recoveryDate `2026-06-08T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `502` / recoverable `6a20e22b1021c0c1fbdde554` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `Viernes 17:00` / recovered `true`
  cancelledWeek `2026-06-01T02:25:47.162000+00:00` / recoveryDate `2026-06-12T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `509` / recoverable `6a22a8071021c0c1fbde2f03` / cause `ambiguous_section`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T10:42:15.427000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `516` / recoverable `6a26aab41021c0c1fbdea0dd` / cause `ambiguous_section`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T11:42:44.223000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `548` / recoverable `6a3023851021c0c1fbe1128f` / cause `ambiguous_section`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T16:08:37.774000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### alejandra giulianelli - `alejandra_giulianelli@hotmail.com`

- legacy user id: `68973bc9418f2e9a6b6cbef4`
- current match status: `matched`
- current app user: `alejandra_giulianelli@hotmail.com` / id `33`
- blocked rows in this bucket: **6**

- source `291` / recoverable `69bfda3dfbd57cfb0e5731b3` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-16T12:02:05.103000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `387` / recoverable `6a02523a2d3685d81683376f` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T22:03:38.428000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `435` / recoverable `6a11f1e61021c0c1fbd9bad6` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T18:28:54.895000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `485` / recoverable `6a1e4de11021c0c1fbdd1545` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T03:28:33.417000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `549` / recoverable `6a3039471021c0c1fbe11873` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T17:41:27.456000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `590` / recoverable `6a37f1831021c0c1fbe310fc` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T14:13:23.200000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### alina guagliano - `alinaguagliano26@gmail.com`

- legacy user id: `695314e5f61c580ccf81f83f`
- current match status: `matched`
- current app user: `alinaguagliano26@gmail.com` / id `44`
- blocked rows in this bucket: **6**

- source `236` / recoverable `69842a4ef61c580ccf77b4c3` / cause `ambiguous_section`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T05:27:42.423000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `310` / recoverable `69cc47f2e85c03079de0252f` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T22:17:22.539000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `329` / recoverable `69dbaa46e85c03079de32fa9` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T14:20:54.025000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `330` / recoverable `69dbaa61e85c03079de33093` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T14:21:21.875000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `401` / recoverable `6a05cae61021c0c1fbd7961c` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T13:15:18.426000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `426` / recoverable `6a0f567f1021c0c1fbd965ff` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T19:01:19.664000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### alondra ruiz - `aloruiz88@gmail.com`

- legacy user id: `69a9bd9da777fa9be0039146`
- current match status: `matched`
- current app user: `aloruiz88@gmail.com` / id `72`
- blocked rows in this bucket: **1**

- source `575` / recoverable `6a3400d01021c0c1fbe230be` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T14:29:36.816000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### ana clara palombo - `anaclarapalombo@hotmail.com`

- legacy user id: `69cabd8bb4cdddc241b1a709`
- current match status: `matched`
- current app user: `anaclarapalombo@hotmail.com` / id `76`
- blocked rows in this bucket: **5**

- source `338` / recoverable `69e0e715e85c03079de46d6d` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T13:41:41.065000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `357` / recoverable `69ea91bde85c03079de61d6b` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-20T21:40:13.308000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `405` / recoverable `6a063cd71021c0c1fbd7b64c` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T21:21:27.859000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `428` / recoverable `6a0f764d1021c0c1fbd975b7` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T21:17:01.502000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `582` / recoverable `6a345e301021c0c1fbe294cc` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T21:08:00.948000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### ana paz reybet - `anapazreybet@hotmail.com`

- legacy user id: `6838c30724d4d1b7adb014be`
- current match status: `matched`
- current app user: `anapazreybet@hotmail.com` / id `4`
- blocked rows in this bucket: **2**

- source `420` / recoverable `6a0e10991021c0c1fbd90e97` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T19:50:49.109000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `608` / recoverable `6a3af1e91021c0c1fbe3def3` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T20:51:53.044000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### ana virgili - `anivirgili83@gmail.com`

- legacy user id: `6949a4acf61c580ccf5bcdc3`
- current match status: `matched`
- current app user: `anivirgili83@gmail.com` / id `43`
- blocked rows in this bucket: **4**

- source `276` / recoverable `69aeb59aa777fa9be0296a0c` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T11:57:14.699000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `283` / recoverable `69b2a610a777fa9be04ed52e` / cause `ambiguous_section`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T11:40:00.360000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `345` / recoverable `69e658e9e85c03079de52bec` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-20T16:48:41.253000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `400` / recoverable `6a05c2e91021c0c1fbd79045` / cause `ambiguous_section`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T12:41:13.114000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### antonela vignolo - `vignoloantonela@gmail.com`

- legacy user id: `6912331618c10abc35d45c18`
- current match status: `matched`
- current app user: `vignoloantonela@gmail.com` / id `41`
- blocked rows in this bucket: **5**

- source `271` / recoverable `69a80d02a777fa9be0e913c4` / cause `ambiguous_section`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-02T10:44:18.182000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `361` / recoverable `69f1111fe85c03079de71bc6` / cause `ambiguous_section`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-27T19:57:19.973000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `362` / recoverable `69f11146e85c03079de71db7` / cause `ambiguous_section`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-27T19:57:58.122000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `418` / recoverable `6a0d191d1021c0c1fbd8d2e3` / cause `ambiguous_section`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T02:14:53.281000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `615` / recoverable `6a3bb3211021c0c1fbe41b05` / cause `ambiguous_section`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T10:36:17.028000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### ariana seghezzo - `arianaseghezzo1@gmail.com`

- legacy user id: `69654495f61c580ccfc25259`
- current match status: `matched`
- current app user: `arianaseghezzo1@gmail.com` / id `48`
- blocked rows in this bucket: **4**

- source `367` / recoverable `69f90d7f6e43b612a8d5e96c` / cause `ambiguous_section`
  original `Lunes 19:00` -> assigned `Viernes 09:00` / recovered `true`
  cancelledWeek `2026-05-04T21:19:59.439000+00:00` / recoveryDate `2026-06-12T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `497` / recoverable `6a209d1d1021c0c1fbddc5e1` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T21:31:09.722000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `498` / recoverable `6a209d441021c0c1fbddc6ff` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T21:31:48.558000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `529` / recoverable `6a28a8f41021c0c1fbdf818a` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T23:59:48.284000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### aylén ferrero paget - `ferreropagetaylen@gmail.com`

- legacy user id: `69efa045e85c03079de6c548`
- current match status: `matched`
- current app user: `ferreropagetaylen@gmail.com` / id `93`
- blocked rows in this bucket: **1**

- source `440` / recoverable `6a14223b1021c0c1fbd9d195` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T10:19:39.848000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### barbara roots - `barbara_roots@hotmail.com`

- legacy user id: `6a1851e31021c0c1fbdb998d`
- current match status: `matched`
- current app user: `barbara_roots@hotmail.com` / id `112`
- blocked rows in this bucket: **2**

- source `543` / recoverable `6a2c197f1021c0c1fbe0b042` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `Miércoles 17:00` / recovered `true`
  cancelledWeek `2026-06-08T14:36:47.529000+00:00` / recoveryDate `2026-06-17T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `583` / recoverable `6a353fd31021c0c1fbe2c0fc` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T13:10:43.656000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### berenice di stefano - `berediste@gmail.com`

- legacy user id: `6839abe324d4d1b7adb09059`
- current match status: `matched`
- current app user: `berediste@gmail.com` / id `14`
- blocked rows in this bucket: **3**

- source `167` / recoverable `6927323e65b641b09e3303a1` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-24T17:00:46.918000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `325` / recoverable `69d6c2c8e85c03079de2b640` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T21:04:08.428000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `459` / recoverable `6a15f3071021c0c1fbdad182` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T19:22:47.523000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### betina delbaldo - `bmdelbaldo@gmail.com`

- legacy user id: `6838c77124d4d1b7adb01ffa`
- current match status: `matched`
- current app user: `bmdelbaldo@gmail.com` / id `6`
- blocked rows in this bucket: **10**

- source `286` / recoverable `69b32ed6a777fa9be05135b8` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T21:23:34.628000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `316` / recoverable `69ce58a3e85c03079de08bda` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T11:53:07.191000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `332` / recoverable `69dd4399e85c03079de3754f` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T19:27:21.949000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `402` / recoverable `6a05f5681021c0c1fbd79adc` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T16:16:40.560000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `416` / recoverable `6a0cd6f71021c0c1fbd8c1b8` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T21:32:39.221000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `417` / recoverable `6a0cd70b1021c0c1fbd8c2cc` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T21:32:59.172000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `486` / recoverable `6a1ef91b1021c0c1fbdd30cd` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T15:39:07.813000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `505` / recoverable `6a21d72d1021c0c1fbde0a1b` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T19:51:09.155000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `538` / recoverable `6a2b26f51021c0c1fbe0867f` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T21:21:57.051000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `606` / recoverable `6a3aeaf71021c0c1fbe3d774` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T20:22:15.894000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### brenda vaquie - `brenvaquie@gmail.com`

- legacy user id: `68751e85437e48d86889b138`
- current match status: `matched`
- current app user: `brenvaquie@gmail.com` / id `31`
- blocked rows in this bucket: **6**

- source `396` / recoverable `6a052fb61021c0c1fbd772bd` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T02:13:10.810000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `397` / recoverable `6a052fcc1021c0c1fbd773eb` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T02:13:32.195000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `414` / recoverable `6a0cc4461021c0c1fbd8b835` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T20:12:54.471000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `531` / recoverable `6a29a3671021c0c1fbdfb626` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T17:48:23.896000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `564` / recoverable `6a31ac221021c0c1fbe1929f` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T20:03:46.375000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `571` / recoverable `6a330d6b1021c0c1fbe1fb56` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T21:11:07.206000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### camila giuliani - `giulianicamila@gmail.com`

- legacy user id: `697c90fff61c580ccf445a2d`
- current match status: `matched`
- current app user: `giulianicamila@gmail.com` / id `52`
- blocked rows in this bucket: **6**

- source `433` / recoverable `6a11a5731021c0c1fbd9b77b` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T13:02:43.538000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `456` / recoverable `6a15d70d1021c0c1fbdabc55` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `Miércoles 09:00` / recovered `true`
  cancelledWeek `2026-05-25T17:23:25.033000+00:00` / recoveryDate `2026-05-27T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `457` / recoverable `6a15d7ad1021c0c1fbdac1eb` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `Miércoles 20:00` / recovered `true`
  cancelledWeek `2026-05-25T17:26:05.150000+00:00` / recoveryDate `2026-06-03T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `504` / recoverable `6a21ac6d1021c0c1fbde0116` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `Viernes 19:00` / recovered `true`
  cancelledWeek `2026-06-01T16:48:45.158000+00:00` / recoveryDate `2026-06-12T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `519` / recoverable `6a26fadb1021c0c1fbded43a` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `Martes 19:00` / recovered `true`
  cancelledWeek `2026-06-08T17:24:43.333000+00:00` / recoveryDate `2026-06-09T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `569` / recoverable `6a32c1af1021c0c1fbe1d0b7` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `Martes 19:00` / recovered `true`
  cancelledWeek `2026-06-15T15:47:59.726000+00:00` / recoveryDate `2026-06-23T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### cecilia pedrido - `pedridoceci@gmail.com`

- legacy user id: `6a2874c61021c0c1fbdf5f61`
- current match status: `matched`
- current app user: `pedridoceci@gmail.com` / id `127`
- blocked rows in this bucket: **4**

- source `534` / recoverable `6a2a13971021c0c1fbe033e0` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T01:47:03.115000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `565` / recoverable `6a31c2b51021c0c1fbe19b34` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `Jueves 17:00` / recovered `true`
  cancelledWeek `2026-06-15T21:40:05.881000+00:00` / recoveryDate `2026-06-18T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `587` / recoverable `6a356f181021c0c1fbe2dada` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T16:32:24.741000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `588` / recoverable `6a356f471021c0c1fbe2dbff` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T16:33:11.459000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### celina lobais - `c.lobais@gmail.com`

- legacy user id: `683afe2124d4d1b7adb0fbd1`
- current match status: `matched`
- current app user: `c.lobais@gmail.com` / id `21`
- blocked rows in this bucket: **1**

- source `201` / recoverable `6949a7aaf61c580ccf5c3688` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-22T20:18:50.993000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### claudia tonarelli - `claudiatonarelli@gmail.com`

- legacy user id: `68b3352e470911da156799cc`
- current match status: `matched`
- current app user: `claudiatonarelli@gmail.com` / id `36`
- blocked rows in this bucket: **5**

- source `213` / recoverable `69667ad6f61c580ccfcb9770` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-12T17:03:18.056000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `227` / recoverable `69791107f61c580ccf1d06bc` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-26T19:24:55.962000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `248` / recoverable `69936dada777fa9be042c2b8` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T19:19:09.729000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `333` / recoverable `69de5e38e85c03079de3ad84` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T15:33:12.823000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `334` / recoverable `69de5e5fe85c03079de3af7c` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T15:33:51.072000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### dana scarafia - `danascarafia@hotmail.com`

- legacy user id: `69fe08c927e24d7c86c461b6`
- current match status: `matched`
- current app user: `danascarafia@hotmail.com` / id `105`
- blocked rows in this bucket: **5**

- source `461` / recoverable `6a15faf31021c0c1fbdad71d` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `Miércoles 20:00` / recovered `true`
  cancelledWeek `2026-05-25T19:56:35.461000+00:00` / recoveryDate `2026-06-24T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `481` / recoverable `6a1d65c11021c0c1fbdcafd5` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T10:58:09.841000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `558` / recoverable `6a30b43a1021c0c1fbe14f3b` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T02:26:02.297000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `592` / recoverable `6a38a07b1021c0c1fbe32c10` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T02:39:55.232000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `610` / recoverable `6a3b00231021c0c1fbe3f021` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T21:52:35.055000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### delfina bonci - `delfinagomezbonci@gmail.com`

- legacy user id: `6a199ba91021c0c1fbdc4ef4`
- current match status: `matched`
- current app user: `delfinagomezbonci@gmail.com` / id `116`
- blocked rows in this bucket: **1**

- source `563` / recoverable `6a319d881021c0c1fbe18b2c` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T19:01:28.576000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### delfina fantino - `delfinafantino@gmail.com`

- legacy user id: `69809730f61c580ccf5b2f45`
- current match status: `matched`
- current app user: `delfinafantino@gmail.com` / id `55`
- blocked rows in this bucket: **4**

- source `305` / recoverable `69cb1b8fe85c03079ddfccbd` / cause `ambiguous_section`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T00:55:43.162000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `398` / recoverable `6a05b4661021c0c1fbd78291` / cause `ambiguous_section`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T11:39:18.367000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `443` / recoverable `6a14509b1021c0c1fbd9e096` / cause `ambiguous_section`
  original `Martes 09:00` -> assigned `Viernes 09:00` / recovered `true`
  cancelledWeek `2026-05-25T13:37:31.080000+00:00` / recoveryDate `2026-05-29T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `521` / recoverable `6a275f271021c0c1fbdf1767` / cause `ambiguous_section`
  original `Martes 09:00` -> assigned `Miércoles 09:00` / recovered `true`
  cancelledWeek `2026-06-08T00:32:39.178000+00:00` / recoveryDate `2026-06-10T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### delfina griguelo - `delfigriguelo@gmail.com`

- legacy user id: `697a96e4f61c580ccf353190`
- current match status: `matched`
- current app user: `delfigriguelo@gmail.com` / id `51`
- blocked rows in this bucket: **6**

- source `308` / recoverable `69cc2915e85c03079de01042` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T20:05:41.523000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `309` / recoverable `69cc292ce85c03079de01132` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T20:06:04.365000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `341` / recoverable `69e142e1e85c03079de48169` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T20:13:21.866000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `350` / recoverable `69e7dc4ee85c03079de5935b` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-20T20:21:34.465000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `413` / recoverable `6a0cbca11021c0c1fbd8b3ff` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T19:40:17.354000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `527` / recoverable `6a286ca81021c0c1fbdf56ce` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T19:42:32.755000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### diego gabriel fernandez - `diegogfernandez99@gmail.com`

- legacy user id: `689d0832a7bc02c2bf317d3a`
- current match status: `matched`
- current app user: `diegogfernandez99@gmail.com` / id `34`
- blocked rows in this bucket: **7**

- source `231` / recoverable `698111abf61c580ccf610f06` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T21:05:47.282000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `232` / recoverable `698111caf61c580ccf6121e4` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-02T21:06:18.313000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `297` / recoverable `69c4bc062a1c963ea9ac6025` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-23T04:54:30.025000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `304` / recoverable `69cac878b4cdddc241b1f235` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T19:01:12.382000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `315` / recoverable `69ce4a2be85c03079de08605` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T10:51:23.823000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `421` / recoverable `6a0e1cb51021c0c1fbd91eec` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T20:42:29.528000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `499` / recoverable `6a209d681021c0c1fbddc81a` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T21:32:24.120000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### emma sabbag - `es.emmasabbag@gmail.com`

- legacy user id: `69cac8dfb4cdddc241b1f310`
- current match status: `matched`
- current app user: `es.emmasabbag@gmail.com` / id `77`
- blocked rows in this bucket: **2**

- source `447` / recoverable `6a14a4cc1021c0c1fbd9f68f` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T19:36:44.779000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `544` / recoverable `6a2d8cdd1021c0c1fbe0dde4` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T17:01:17.958000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### estefania bellomo - `estefybellomo@hotmail.com`

- legacy user id: `6838c78a24d4d1b7adb02044`
- current match status: `matched`
- current app user: `estefybellomo@hotmail.com` / id `7`
- blocked rows in this bucket: **4**

- source `23` / recoverable `688ce792584e00089e950791` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-07-28T16:13:06.705000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `192` / recoverable `693c4d47f61c580ccf214c41` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T17:13:43.836000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `224` / recoverable `6973a239f61c580ccf1036bf` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T16:30:49.338000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `230` / recoverable `697d03b1f61c580ccf4e4983` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-26T19:17:05.864000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### estefanía ronconi - `estefania.ronconic@gmail.com`

- legacy user id: `69681da5f61c580ccfdf03f4`
- current match status: `matched`
- current app user: `estefania.ronconic@gmail.com` / id `49`
- blocked rows in this bucket: **3**

- source `265` / recoverable `69a440b3a777fa9be0cb7b7f` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-23T13:35:47.741000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `451` / recoverable `6a1570b91021c0c1fbda78a2` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `Jueves 18:00` / recovered `true`
  cancelledWeek `2026-05-25T10:06:49.376000+00:00` / recoveryDate `2026-05-28T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `512` / recoverable `6a25b9551021c0c1fbde820a` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T18:32:53.676000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### evangelina reglero - `regleroevangelina@gmail.com`

- legacy user id: `69d63cdee85c03079de25529`
- current match status: `matched`
- current app user: `regleroevangelina@gmail.com` / id `84`
- blocked rows in this bucket: **3**

- source `462` / recoverable `6a1612991021c0c1fbdae4ea` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T21:37:29.941000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `488` / recoverable `6a1f49051021c0c1fbdd5ec3` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T21:20:05.358000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `524` / recoverable `6a2796f51021c0c1fbdf28ad` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T04:30:45.642000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### francisco pons - `franciscopons2001@gmail.com`

- legacy user id: `6a1db7b71021c0c1fbdcd01f`
- current match status: `matched`
- current app user: `franciscopons2001@gmail.com` / id `120`
- blocked rows in this bucket: **3**

- source `525` / recoverable `6a27e1f81021c0c1fbdf2ad6` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `Lunes 19:00` / recovered `true`
  cancelledWeek `2026-06-08T09:50:48.513000+00:00` / recoveryDate `2026-06-22T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `559` / recoverable `6a311a811021c0c1fbe15b86` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T09:42:25.859000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `605` / recoverable `6a3a86551021c0c1fbe3b80e` / cause `ambiguous_section`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T13:12:53.578000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### gianella mattioli - `gianemattioli@gmail.com`

- legacy user id: `6a1872101021c0c1fbdbbbfb`
- current match status: `matched`
- current app user: `gianemattioli@gmail.com` / id `113`
- blocked rows in this bucket: **1**

- source `560` / recoverable `6a3134821021c0c1fbe1640e` / cause `ambiguous_section`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T11:33:22.776000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### gisela velasco - `gvelasco79@gmail.com`

- legacy user id: `6a19fe4b1021c0c1fbdc6556`
- current match status: `matched`
- current app user: `gvelasco79@gmail.com` / id `117`
- blocked rows in this bucket: **1**

- source `609` / recoverable `6a3afeec1021c0c1fbe3e9dd` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `Miércoles 20:00` / recovered `true`
  cancelledWeek `2026-06-22T21:47:24.379000+00:00` / recoveryDate `2026-06-24T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### guillermina quiroga - `guillequiroga3116@gmail.com`

- legacy user id: `68f280013d5cf39df1406a67`
- current match status: `matched`
- current app user: `guillequiroga3116@gmail.com` / id `37`
- blocked rows in this bucket: **4**

- source `270` / recoverable `69a7811ba777fa9be0e7a48b` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-02T00:47:23.920000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `298` / recoverable `69c511592a1c963ea9ac644f` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-23T10:58:33.948000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `335` / recoverable `69dea45fe85c03079de3c3c4` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T20:32:31.730000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `394` / recoverable `6a0398322d3685d816839b60` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T21:14:26.758000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### jazmin banchio - `jazchubanchio@gmail.com`

- legacy user id: `69cd1b6de85c03079de062c0`
- current match status: `matched`
- current app user: `jazchubanchio@gmail.com` / id `79`
- blocked rows in this bucket: **1**

- source `573` / recoverable `6a33c65c1021c0c1fbe21df9` / cause `ambiguous_section`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T10:20:12.779000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### julia aguaya - `juliag2020@outlook.com`

- legacy user id: `69d3cc4be85c03079de0d2cf`
- current match status: `matched`
- current app user: `juliag2020@outlook.com` / id `80`
- blocked rows in this bucket: **9**

- source `381` / recoverable `6a0217ef2d3685d816831536` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `Martes 09:00` / recovered `true`
  cancelledWeek `2026-05-11T17:54:55.898000+00:00` / recoveryDate `2026-06-02T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `395` / recoverable `6a04f6c71021c0c1fbd75ff4` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `Miércoles 18:00` / recovered `true`
  cancelledWeek `2026-05-11T22:10:15.617000+00:00` / recoveryDate `2026-06-10T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `411` / recoverable `6a0c82681021c0c1fbd8a452` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `Viernes 19:00` / recovered `true`
  cancelledWeek `2026-05-18T15:31:52.755000+00:00` / recoveryDate `2026-06-26T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `450` / recoverable `6a1512851021c0c1fbda6986` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T03:24:53.640000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `455` / recoverable `6a1594941021c0c1fbdaa5b7` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `Jueves 20:00` / recovered `true`
  cancelledWeek `2026-05-25T12:39:48.477000+00:00` / recoveryDate `2026-06-18T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `480` / recoverable `6a1d648a1021c0c1fbdcaa14` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `Jueves 20:00` / recovered `true`
  cancelledWeek `2026-06-01T10:52:58.692000+00:00` / recoveryDate `2026-06-25T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `489` / recoverable `6a1f67e11021c0c1fbdd6438` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T23:31:45.156000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `517` / recoverable `6a26acae1021c0c1fbdea5cf` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T11:51:10.444000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `530` / recoverable `6a2951221021c0c1fbdf997c` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T11:57:22.570000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### julieta bailaque - `julietab17@hotmail.com`

- legacy user id: `6a1b06f41021c0c1fbdc821c`
- current match status: `matched`
- current app user: `julietab17@hotmail.com` / id `118`
- blocked rows in this bucket: **1**

- source `570` / recoverable `6a32f0ad1021c0c1fbe1e000` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T19:08:29.256000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### julieta oldani - `julioldani53@gmail.com`

- legacy user id: `69a1bfc7a777fa9be0bbb1e4`
- current match status: `matched`
- current app user: `julioldani53@gmail.com` / id `63`
- blocked rows in this bucket: **2**

- source `520` / recoverable `6a270e9d1021c0c1fbdee3c7` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `Viernes 18:00` / recovered `true`
  cancelledWeek `2026-06-08T18:49:01.545000+00:00` / recoveryDate `2026-06-12T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `553` / recoverable `6a30747c1021c0c1fbe12eb1` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `Jueves 18:00` / recovered `true`
  cancelledWeek `2026-06-15T21:54:04.114000+00:00` / recoveryDate `2026-06-18T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### karine freitas - `karinefreitasdefaria.kf@gmail.com`

- legacy user id: `69a35ebba777fa9be0c8d307`
- current match status: `matched`
- current app user: `karinefreitasdefaria.kf@gmail.com` / id `69`
- blocked rows in this bucket: **1**

- source `536` / recoverable `6a2ac8b81021c0c1fbe0507a` / cause `ambiguous_section`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T14:39:52.486000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### lara blunda - `laraeevs@gmail.com`

- legacy user id: `69f74def6e43b612a8d58595`
- current match status: `matched`
- current app user: `laraeevs@gmail.com` / id `100`
- blocked rows in this bucket: **4**

- source `412` / recoverable `6a0cbc491021c0c1fbd8b1e7` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `Miércoles 08:00` / recovered `true`
  cancelledWeek `2026-05-18T19:38:49.475000+00:00` / recoveryDate `2026-06-17T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `552` / recoverable `6a30557f1021c0c1fbe12583` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T19:41:51.678000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `584` / recoverable `6a35559d1021c0c1fbe2c8db` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T14:43:41.227000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `585` / recoverable `6a3555aa1021c0c1fbe2c9ff` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T14:43:54.563000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### lara olivera - `lara.olivera@hotmail.com`

- legacy user id: `6862f6d267c2c7e758ba9b85`
- current match status: `matched`
- current app user: `lara.olivera@hotmail.com` / id `28`
- blocked rows in this bucket: **4**

- source `296` / recoverable `69c440c92a1c963ea9ac1ace` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `Miércoles 20:00` / recovered `true`
  cancelledWeek `2026-03-23T20:08:41.681000+00:00` / recoveryDate `2026-06-03T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `317` / recoverable `69d28557e85c03079de0a17c` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `Lunes 18:00` / recovered `true`
  cancelledWeek `2026-03-30T15:52:55.009000+00:00` / recoveryDate `2026-06-22T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `318` / recoverable `69d28569e85c03079de0a25d` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T15:53:13.321000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `496` / recoverable `6a20856b1021c0c1fbddb484` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T19:50:03.264000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### laura prece - `lauraprece@hotmail.com`

- legacy user id: `69a1be06a777fa9be0baddf3`
- current match status: `matched`
- current app user: `lauraprece@hotmail.com` / id `62`
- blocked rows in this bucket: **1**

- source `351` / recoverable `69e8b869e85c03079de5a9f3` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-20T12:00:41.574000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### lila grigüelo - `griguelolila@gmail.com`

- legacy user id: `68af80aa65a2e69a26a84afd`
- current match status: `matched`
- current app user: `griguelolila@gmail.com` / id `35`
- blocked rows in this bucket: **1**

- source `364` / recoverable `69f11949e85c03079de7330a` / cause `ambiguous_section`
  original `Martes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-27T20:32:09.472000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### lucia ingaramo - `luciav.ingaramo@gmail.com`

- legacy user id: `683af38a24d4d1b7adb0eeb6`
- current match status: `matched`
- current app user: `luciav.ingaramo@gmail.com` / id `20`
- blocked rows in this bucket: **8**

- source `313` / recoverable `69cd9055e85c03079de074b4` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `Viernes 17:00` / recovered `true`
  cancelledWeek `2026-03-30T21:38:29.933000+00:00` / recoveryDate `2026-06-19T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `322` / recoverable `69d40df5e85c03079de0e260` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `Miércoles 18:00` / recovered `true`
  cancelledWeek `2026-04-06T19:48:05.908000+00:00` / recoveryDate `2026-06-24T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `386` / recoverable `6a023e012d3685d8168326c4` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T20:37:21.864000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `419` / recoverable `6a0e05fe1021c0c1fbd904cd` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T19:05:34.918000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `449` / recoverable `6a150a5b1021c0c1fbda6755` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T02:50:03.060000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `547` / recoverable `6a301db31021c0c1fbe10daf` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T15:43:47.885000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `613` / recoverable `6a3b32521021c0c1fbe41066` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T01:26:42.043000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `614` / recoverable `6a3b32fe1021c0c1fbe4139f` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T01:29:34.814000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### luciana castellani - `luciana.castellani@hotmail.com`

- legacy user id: `6838bd5f24d4d1b7adb01017`
- current match status: `matched`
- current app user: `luciana.castellani@hotmail.com` / id `2`
- blocked rows in this bucket: **2**

- source `385` / recoverable `6a023b4c2d3685d816832185` / cause `ambiguous_section`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T20:25:48.532000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `600` / recoverable `6a3995401021c0c1fbe37105` / cause `ambiguous_section`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T20:04:16.299000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### luciana rolle - `rolleluciana@gmail.com`

- legacy user id: `6839ac8c24d4d1b7adb0943c`
- current match status: `matched`
- current app user: `rolleluciana@gmail.com` / id `15`
- blocked rows in this bucket: **4**

- source `87` / recoverable `68d4426fc11c04213f92fc6d` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-22T19:11:43.445000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `403` / recoverable `6a0628aa1021c0c1fbd7a329` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T19:55:22.315000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `540` / recoverable `6a2b42c51021c0c1fbe08fa5` / cause `ambiguous_section`
  original `Viernes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T23:20:37.108000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `26` / recoverable `6890890c584e00089eb56c4f` / cause `inconsistent_state`
  original `Miércoles 19:00` -> assigned `Lunes 18:00` / recovered `false`
  cancelledWeek `2025-08-04T10:18:52.989000+00:00` / recoveryDate `2025-08-11T16:22:10.069000+00:00` / possible sections `reformer_arriba | reformer_abajo`
  secondary blockers: ambiguous_section
  detail: Recovered=false but assigned slot or recoveryDate is unexpectedly present.

### lucía primo brochiero - `luciabrochiero@gmail.com`

- legacy user id: `69f09489e85c03079de6ef06`
- current match status: `matched`
- current app user: `luciabrochiero@gmail.com` / id `94`
- blocked rows in this bucket: **3**

- source `399` / recoverable `6a05b64a1021c0c1fbd784e0` / cause `ambiguous_section`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T11:47:22.329000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `535` / recoverable `6a2a14411021c0c1fbe03757` / cause `ambiguous_section`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T01:49:53.039000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `602` / recoverable `6a39e9ab1021c0c1fbe3889d` / cause `ambiguous_section`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T02:04:27.827000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### maddalena badas - `maddyyb4@gmail.com`

- legacy user id: `69ded466e85c03079de3dc86`
- current match status: `matched`
- current app user: `maddyyb4@gmail.com` / id `90`
- blocked rows in this bucket: **2**

- source `464` / recoverable `6a163ff41021c0c1fbdaf269` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T00:51:00.588000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `545` / recoverable `6a2e0d701021c0c1fbe0e493` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T02:09:52.191000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### madelaine fregenal - `madelainefregenal@gmail.com`

- legacy user id: `6908c4b1123d0671aede04d2`
- current match status: `matched`
- current app user: `madelainefregenal@gmail.com` / id `39`
- blocked rows in this bucket: **4**

- source `252` / recoverable `69961c91a777fa9be053c1a4` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-02-16T20:09:53.264000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `295` / recoverable `69c40e772a1c963ea9ac0873` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-23T16:33:59.167000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `337` / recoverable `69dfe108e85c03079de411f6` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T19:03:36.943000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `410` / recoverable `6a0b54da1021c0c1fbd86a1d` / cause `ambiguous_section`
  original `Lunes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T18:05:14.845000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### malena altamirano - `malenaaltamirano@gmail.com`

- legacy user id: `69f4abda6e43b612a8d56dee`
- current match status: `matched`
- current app user: `malenaaltamirano@gmail.com` / id `99`
- blocked rows in this bucket: **1**

- source `372` / recoverable `69fcacc927e24d7c86c41665` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T15:16:25.658000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### malena navarro - `malenanavarro12@gmail.com`

- legacy user id: `69f3bd516e43b612a8d56123`
- current match status: `matched`
- current app user: `malenanavarro12@gmail.com` / id `97`
- blocked rows in this bucket: **3**

- source `388` / recoverable `6a025ad82d3685d816834321` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T22:40:24.050000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `518` / recoverable `6a26c30d1021c0c1fbdebe91` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T13:26:37.564000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `528` / recoverable `6a2874de1021c0c1fbdf62b3` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T20:17:34.409000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### maria bergero - `mariaagustinabergero@gmail.com`

- legacy user id: `69fbbcf927e24d7c86c3dd8f`
- current match status: `matched`
- current app user: `mariaagustinabergero@gmail.com` / id `104`
- blocked rows in this bucket: **1**

- source `554` / recoverable `6a30859d1021c0c1fbe137cd` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `Miércoles 08:00` / recovered `true`
  cancelledWeek `2026-06-15T23:07:09.036000+00:00` / recoveryDate `2026-06-17T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### maria florencia planiscig - `florplaniscig5@gmail.com`

- legacy user id: `6838dc2824d4d1b7adb046e8`
- current match status: `matched`
- current app user: `florplaniscig5@gmail.com` / id `10`
- blocked rows in this bucket: **6**

- source `219` / recoverable `696ea6f0f61c580ccff4ed9f` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-19T21:49:36.815000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `272` / recoverable `69a89ea2a777fa9be0ec5bc8` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-02T21:05:38.810000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `280` / recoverable `69b1dabaa777fa9be04ae6ef` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T21:12:26.984000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `326` / recoverable `69d6c951e85c03079de2b84a` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T21:32:01.237000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `468` / recoverable `6a173f3b1021c0c1fbdb352e` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T19:00:11.016000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `617` / recoverable `6a3c3b051021c0c1fbe43fe7` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T20:16:05.714000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### maria ines gonzalez ibarra - `enam1007@hotmail.es`

- legacy user id: `683dbb1d24d4d1b7adb161d5`
- current match status: `matched`
- current app user: `enam1007@hotmail.es` / id `23`
- blocked rows in this bucket: **4**

- source `273` / recoverable `69a968d2a777fa9be0f89f92` / cause `ambiguous_section`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-02T11:28:18.543000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `281` / recoverable `69b1eef0a777fa9be04b960c` / cause `ambiguous_section`
  original `Jueves 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T22:38:40.805000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `371` / recoverable `69fb23c927e24d7c86c3b49f` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T11:19:37.360000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `466` / recoverable `6a16da311021c0c1fbdb1371` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T11:49:05.460000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### maria paola lopez - `maripalopez@live.com`

- legacy user id: `69a1da29a777fa9be0bcf081`
- current match status: `matched`
- current app user: `maripalopez@live.com` / id `64`
- blocked rows in this bucket: **1**

- source `568` / recoverable `6a328e3f1021c0c1fbe1bef1` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T12:08:31.895000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### mariela homs - `marielhoms@gmail.com`

- legacy user id: `697ccdc7f61c580ccf4d0a35`
- current match status: `matched`
- current app user: `marielhoms@gmail.com` / id `53`
- blocked rows in this bucket: **5**

- source `275` / recoverable `69aeac12a777fa9be028ffaa` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `Martes 09:00` / recovered `true`
  cancelledWeek `2026-03-09T11:16:34.621000+00:00` / recoveryDate `2026-06-23T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `311` / recoverable `69ccfdaee85c03079de03977` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T11:12:46.162000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `320` / recoverable `69d39927e85c03079de0bd3f` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T11:29:43.442000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `515` / recoverable `6a26a08c1021c0c1fbde9bd6` / cause `ambiguous_section`
  original `Lunes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T10:59:24.040000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `616` / recoverable `6a3bc71f1021c0c1fbe42907` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T12:01:35.217000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### martina aguirre - `martina.a890@gmail.com`

- legacy user id: `683b088924d4d1b7adb10cd6`
- current match status: `matched`
- current app user: `martina.a890@gmail.com` / id `22`
- blocked rows in this bucket: **7**

- source `269` / recoverable `69a76a2ba777fa9be0e5c183` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-02T23:09:31.918000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `284` / recoverable `69b2c40ba777fa9be04f03e2` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-09T13:47:55.236000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `343` / recoverable `69e275c2e85c03079de4a1ff` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T18:02:42.837000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `354` / recoverable `69ea5e32e85c03079de5d9bf` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-20T18:00:18.565000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `374` / recoverable `69fcca6527e24d7c86c41e1a` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T17:22:45.742000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `579` / recoverable `6a3438dc1021c0c1fbe24f9c` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T18:28:44.128000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `586` / recoverable `6a3559771021c0c1fbe2d1d1` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T15:00:07.188000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### martina guridi - `martinagurididelbaldo@gmail.com`

- legacy user id: `683e1a9d54c3c5d82dd8267d`
- current match status: `matched`
- current app user: `martinagurididelbaldo@gmail.com` / id `24`
- blocked rows in this bucket: **5**

- source `382` / recoverable `6a022a492d3685d81683174d` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `Miércoles 20:00` / recovered `true`
  cancelledWeek `2026-05-11T19:13:13.216000+00:00` / recoveryDate `2026-06-03T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `409` / recoverable `6a0b51b41021c0c1fbd86328` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `Viernes 18:00` / recovered `true`
  cancelledWeek `2026-05-18T17:51:48.873000+00:00` / recoveryDate `2026-06-05T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `483` / recoverable `6a1dd98c1021c0c1fbdce03d` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `Viernes 19:00` / recovered `true`
  cancelledWeek `2026-06-01T19:12:12.023000+00:00` / recoveryDate `2026-06-19T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `594` / recoverable `6a3934e91021c0c1fbe34541` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T13:13:13.152000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `598` / recoverable `6a3987b21021c0c1fbe36509` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T19:06:26.244000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### melisa mazzei - `melisamazzei@gmail.com`

- legacy user id: `6a0af5c01021c0c1fbd83db1`
- current match status: `matched`
- current app user: `melisamazzei@gmail.com` / id `108`
- blocked rows in this bucket: **2**

- source `452` / recoverable `6a1579681021c0c1fbda7e25` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `Martes 09:00` / recovered `true`
  cancelledWeek `2026-05-25T10:43:52.854000+00:00` / recoveryDate `2026-05-26T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `599` / recoverable `6a398bf51021c0c1fbe36cfa` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T19:24:37.743000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### melisa sciutto - `melisa.ss41011@gmail.com`

- legacy user id: `69a3167ba777fa9be0c63fac`
- current match status: `matched`
- current app user: `melisa.ss41011@gmail.com` / id `68`
- blocked rows in this bucket: **1**

- source `506` / recoverable `6a21f5361021c0c1fbde1671` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `Martes 20:00` / recovered `true`
  cancelledWeek `2026-06-01T21:59:18.307000+00:00` / recoveryDate `2026-06-09T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### micaela anabel roatta - `micaroatta@gmail.com`

- legacy user id: `695d48aef61c580ccf9271e1`
- current match status: `matched`
- current app user: `micaroatta@gmail.com` / id `46`
- blocked rows in this bucket: **2**

- source `522` / recoverable `6a2766bb1021c0c1fbdf1ce1` / cause `ambiguous_section`
  original `Martes 07:00` -> assigned `Martes 08:00` / recovered `true`
  cancelledWeek `2026-06-08T01:04:59.564000+00:00` / recoveryDate `2026-06-23T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `601` / recoverable `6a39a3bf1021c0c1fbe37e55` / cause `ambiguous_section`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T21:06:07.624000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### micaela rad - `micaela.rad15@gmail.com`

- legacy user id: `6870f8e0437e48d8686c7a0a`
- current match status: `matched`
- current app user: `micaela.rad15@gmail.com` / id `30`
- blocked rows in this bucket: **14**

- source `82` / recoverable `68c92fde42a86feb87600554` / cause `ambiguous_section`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-15T09:37:34.963000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `90` / recoverable `68db4cb4ff8230f50718fd26` / cause `ambiguous_section`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-09-29T03:21:24.777000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `103` / recoverable `68edcdcb83c46bbb4eebb367` / cause `ambiguous_section`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-13T04:12:59.937000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `120` / recoverable `69003b33e57700f7772b8852` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-10-27T03:40:35.923000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `127` / recoverable `690c19b287e38f3612118ee0` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-11-03T03:44:50.759000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `187` / recoverable `693a1513f61c580ccf11079e` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-12-08T00:49:23.292000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `204` / recoverable `695c7ff0f61c580ccf8fd27b` / cause `ambiguous_section`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T03:22:24.822000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `207` / recoverable `695f3d21f61c580ccfa68cb2` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-05T05:14:09.930000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `314` / recoverable `69cdb816e85c03079de0801b` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-30T00:28:06.846000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `423` / recoverable `6a0e8b8b1021c0c1fbd93517` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T04:35:23.410000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `437` / recoverable `6a135dcc1021c0c1fbd9c4b6` / cause `ambiguous_section`
  original `Martes 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T20:21:32.937000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `469` / recoverable `6a17b8a71021c0c1fbdb6ab5` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T03:38:15.751000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `470` / recoverable `6a17b8c91021c0c1fbdb6be5` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T03:38:49.342000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `572` / recoverable `6a33ba7c1021c0c1fbe21bbc` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T09:29:32.433000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### monica gimenez - `nikigimenez18@gmail.com`

- legacy user id: `6a2adbb41021c0c1fbe05988`
- current match status: `matched`
- current app user: `nikigimenez18@gmail.com` / id `129`
- blocked rows in this bucket: **1**

- source `596` / recoverable `6a3974d31021c0c1fbe35e0b` / cause `ambiguous_section`
  original `Lunes 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T17:45:55.410000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### monica melgarejo - `profesoramonicamelgarejo@hotmail.com`

- legacy user id: `6851e40d1f26ed9b2d3cd112`
- current match status: `matched`
- current app user: `profesoramonicamelgarejo@hotmail.com` / id `27`
- blocked rows in this bucket: **10**

- source `278` / recoverable `69b09547a777fa9be042d91b` / cause `ambiguous_section`
  original `Jueves 08:00` -> assigned `Miércoles 08:00` / recovered `true`
  cancelledWeek `2026-03-09T22:03:51.191000+00:00` / recoveryDate `2026-06-03T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `293` / recoverable `69c32d3a2a1c963ea9ab988c` / cause `ambiguous_section`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-23T00:32:58.302000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `319` / recoverable `69d3876ce85c03079de0b29a` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-06T10:14:04.248000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `331` / recoverable `69dc3919e85c03079de33df6` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T00:30:17.279000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `445` / recoverable `6a1468161021c0c1fbd9ebee` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T15:17:42.831000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `479` / recoverable `6a1cc4071021c0c1fbdc96d1` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T23:28:07.151000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `490` / recoverable `6a2003eb1021c0c1fbdd6df2` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T10:37:31.445000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `491` / recoverable `6a20047e1021c0c1fbdd7457` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T10:39:58.133000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `513` / recoverable `6a25c1da1021c0c1fbde84e2` / cause `ambiguous_section`
  original `Lunes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T19:09:14.199000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `532` / recoverable `6a29baf81021c0c1fbdfc36f` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T19:28:56.962000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### natalia morello - `nataliamorello@hotmail.com`

- legacy user id: `6839a86624d4d1b7adb07ff0`
- current match status: `matched`
- current app user: `nataliamorello@hotmail.com` / id `13`
- blocked rows in this bucket: **1**

- source `214` / recoverable `6967e99ef61c580ccfd8d43b` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-01-12T19:08:14.426000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### patricia battaglia - `patribattagl@gmail.com`

- legacy user id: `69f8881d6e43b612a8d5a974`
- current match status: `matched`
- current app user: `patribattagl@gmail.com` / id `101`
- blocked rows in this bucket: **3**

- source `370` / recoverable `69fa41cd27e24d7c86c3939d` / cause `ambiguous_section`
  original `Martes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-04T19:15:25.839000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `427` / recoverable `6a0f58091021c0c1fbd96841` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-18T19:07:53.727000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `578` / recoverable `6a3434061021c0c1fbe246cf` / cause `ambiguous_section`
  original `Jueves 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T18:08:06.785000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### paula leotta - `pauleotta@gmail.com`

- legacy user id: `695e55f5f61c580ccf95cd0d`
- current match status: `matched`
- current app user: `pauleotta@gmail.com` / id `47`
- blocked rows in this bucket: **1**

- source `340` / recoverable `69e13b23e85c03079de47b19` / cause `ambiguous_section`
  original `Miércoles 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-04-13T19:40:19.023000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### romina luna - `rominaluna1999@gmail.com`

- legacy user id: `699c5b7ba777fa9be075863f`
- current match status: `matched`
- current app user: `rominaluna1999@gmail.com` / id `58`
- blocked rows in this bucket: **3**

- source `383` / recoverable `6a022fa52d3685d816831953` / cause `ambiguous_section`
  original `Lunes 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T19:36:05.439000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `384` / recoverable `6a022fb32d3685d816831a5b` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-11T19:36:19.983000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `494` / recoverable `6a20745c1021c0c1fbdda9ce` / cause `ambiguous_section`
  original `Miércoles 17:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T18:37:16.689000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### romina rosso - `romi_rosso@outlook.com`

- legacy user id: `69d55b93e85c03079de1ea26`
- current match status: `matched`
- current app user: `romi_rosso@outlook.com` / id `83`
- blocked rows in this bucket: **1**

- source `580` / recoverable `6a344c721021c0c1fbe28ad0` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T19:52:18.865000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### roxana trobbiani - `r.g.chani@gmail.com`

- legacy user id: `69d4d933e85c03079de15250`
- current match status: `matched`
- current app user: `r.g.chani@gmail.com` / id `81`
- blocked rows in this bucket: **3**

- source `346` / recoverable `69e66f5ee85c03079de5382c` / cause `ambiguous_section`
  original `Martes 09:00` -> assigned `Martes 19:00` / recovered `true`
  cancelledWeek `2026-04-20T18:24:30.693000+00:00` / recoveryDate `2026-06-02T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `368` / recoverable `69f94eed6e43b612a8d6813b` / cause `ambiguous_section`
  original `Martes 09:00` -> assigned `Martes 09:00` / recovered `true`
  cancelledWeek `2026-05-04T01:59:09.891000+00:00` / recoveryDate `2026-06-23T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `482` / recoverable `6a1dc0001021c0c1fbdcd802` / cause `ambiguous_section`
  original `Martes 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T17:23:12.555000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### silvia andre garcia - `silvia_77_13@hotmail.com`

- legacy user id: `683985d224d4d1b7adb07997`
- current match status: `matched`
- current app user: `silvia_77_13@hotmail.com` / id `12`
- blocked rows in this bucket: **4**

- source `2` / recoverable `6863ec642e6b6e0973ab8161` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-06-30T14:10:44.607000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `29` / recoverable `68922167a3c918c12b548489` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2025-08-04T15:21:11.048000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `290` / recoverable `69bbf2d7fbd57cfb0e42a705` / cause `ambiguous_section`
  original `Jueves 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-03-16T12:57:59.369000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `487` / recoverable `6a1f2ab51021c0c1fbdd4511` / cause `ambiguous_section`
  original `Martes 19:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-01T19:10:45.266000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### sol arquiel - `solarquiel2008@hotmail.es`

- legacy user id: `69f8ff9f6e43b612a8d5d348`
- current match status: `matched`
- current app user: `solarquiel2008@hotmail.es` / id `102`
- blocked rows in this bucket: **1**

- source `589` / recoverable `6a358b211021c0c1fbe2e2d5` / cause `ambiguous_section`
  original `Viernes 17:00` -> assigned `Viernes 18:00` / recovered `true`
  cancelledWeek `2026-06-15T18:32:01.166000+00:00` / recoveryDate `2026-06-19T00:00:00+00:00` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### tania perez - `taniap2121@hotmail.com`

- legacy user id: `6a29d5671021c0c1fbdffcab`
- current match status: `matched`
- current app user: `taniap2121@hotmail.com` / id `128`
- blocked rows in this bucket: **1**

- source `537` / recoverable `6a2ada751021c0c1fbe05860` / cause `ambiguous_section`
  original `Miércoles 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T15:55:33.922000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### valentina chiavassa - `valechiavassa09@gmail.com`

- legacy user id: `69cad35db4cdddc241b1f81d`
- current match status: `matched`
- current app user: `valechiavassa09@gmail.com` / id `78`
- blocked rows in this bucket: **2**

- source `557` / recoverable `6a30b3fe1021c0c1fbe14d2f` / cause `ambiguous_section`
  original `Martes 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T02:25:02.388000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `577` / recoverable `6a3421a11021c0c1fbe2402a` / cause `ambiguous_section`
  original `Jueves 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T16:49:37.449000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### valeria silvestri - `valery528@hotmail.com`

- legacy user id: `69a1ed57a777fa9be0bea7d9`
- current match status: `matched`
- current app user: `valery528@hotmail.com` / id `66`
- blocked rows in this bucket: **1**

- source `465` / recoverable `6a16cec71021c0c1fbdb0e9a` / cause `ambiguous_section`
  original `Jueves 07:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-05-25T11:00:23.897000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### veronica lizzi - `veronicagabrielalizzi@gmail.com`

- legacy user id: `688a02706c3009473a5d018a`
- current match status: `matched`
- current app user: `veronicagabrielalizzi@gmail.com` / id `32`
- blocked rows in this bucket: **1**

- source `612` / recoverable `6a3b120d1021c0c1fbe408c3` / cause `ambiguous_section`
  original `Miércoles 08:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-22T23:09:01.772000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### victoria fernandez - `fernandez.a.victoria2023@gmail.com`

- legacy user id: `69ea923fe85c03079de61e7c`
- current match status: `matched`
- current app user: `fernandez.a.victoria2023@gmail.com` / id `92`
- blocked rows in this bucket: **2**

- source `476` / recoverable `6a18a1671021c0c1fbdbf31c` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `Viernes 19:00` / recovered `true`
  cancelledWeek `2026-05-25T20:11:19.118000+00:00` / recoveryDate `2026-06-05T00:00:00+00:00` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

- source `539` / recoverable `6a2b3b301021c0c1fbe08b0b` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-08T22:48:16.454000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### victoria mainetti - `viquimainetti@hotmail.com.ar`

- legacy user id: `69f3be786e43b612a8d5660a`
- current match status: `matched`
- current app user: `viquimainetti@hotmail.com.ar` / id `98`
- blocked rows in this bucket: **1**

- source `581` / recoverable `6a3453e21021c0c1fbe29173` / cause `ambiguous_section`
  original `Jueves 18:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T20:24:02.506000+00:00` / recoveryDate `-` / possible sections `cadillac | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.

### victoria michelini - `victoriamichelini52@gmail.com`

- legacy user id: `69f9019b6e43b612a8d5dd5d`
- current match status: `matched`
- current app user: `victoriamichelini52@gmail.com` / id `103`
- blocked rows in this bucket: **1**

- source `561` / recoverable `6a316cd31021c0c1fbe17a48` / cause `ambiguous_section`
  original `Miércoles 09:00` -> assigned `- -` / recovered `false`
  cancelledWeek `2026-06-15T15:33:39.179000+00:00` / recoveryDate `-` / possible sections `reformer_arriba | reformer_abajo`
  detail: Original day/hour maps to more than one possible section.
