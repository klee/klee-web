# Committed Source Transitions

The counts below are additions plus deletions. Each range links to the corresponding public Git comparison.

| ID | Scope | Git range | Files | Additions | Deletions | Changed lines |
|---|---|---|---:|---:|---:|---:|
| C01 | Complete AWS single-VM provider baseline | [`8f31663..71de38e`](https://github.com/FinnLeh/klee-web/compare/8f316635fdef249a05542766e65df5cfbe7bbd61...71de38e8df35ea762a2ca189536fd1bf9d4d3855) | 23 | 1,341 | 25 | 1,366 |
| C02 | Complete AWS role-separation transition | [`71de38e..57883c8`](https://github.com/FinnLeh/klee-web/compare/71de38e8df35ea762a2ca189536fd1bf9d4d3855...57883c80498c3adbcfbdeed84cd0caa8dad14ed8) | 19 | 1,440 | 70 | 1,510 |
| C03 | Complete Azure single-VM provider substitution | [`57883c8..17e5a1c`](https://github.com/FinnLeh/klee-web/compare/57883c80498c3adbcfbdeed84cd0caa8dad14ed8...17e5a1ce044a2d8406c6b0a8096722457b8ed01b) | 10 | 932 | 8 | 940 |
| C04 | Azure role-aware provider integration | [`17e5a1c..a4e5f5c`](https://github.com/FinnLeh/klee-web/compare/17e5a1ce044a2d8406c6b0a8096722457b8ed01b...a4e5f5c834d17c14fff2d3f8ecb1bd8892b33514) | 1 | 2 | 0 | 2 |
| C05 | Complete controlled maintenance lifecycle | [`bc0174a..0fb7942`](https://github.com/FinnLeh/klee-web/compare/bc0174a55b17afeabfcfcbd87e57260f2ea7bb8e...0fb794282143206af18a78ca6d1f79ec7bba3a3b) | 16 | 245 | 4 | 249 |
| C06 | Institutional deployment, upgrade, and scale-out source | [`7dfc433..d9bb115`](https://github.com/FinnLeh/klee-web/compare/7dfc4331aeb0e9a73898fb79a53a7107bf2f4aa7...d9bb115af9489c02b85cd49bf8ab071a9d43f389) | 6 | 171 | 8 | 179 |

C01 begins immediately before `8076efc`, the first AWS deployment-source commit. C03 reconstructs the original Azure-authored transition after its rebase onto the role-aware source. The experimental Azure control was `71de38e`.

C02 contains two additions to the existing AWS single-VM adapter. The file inventory assigns them to `role-aware-provider-integration`, leaving 1,508 lines assigned to `role-separation`. C04 assigns the equivalent two Azure adapter additions to the same accounting unit.

C06 is the reconstructable merged DoC delta. Its frozen experimental control was `0fb7942`, while the source was later rebased onto `7dfc433` before merge.
