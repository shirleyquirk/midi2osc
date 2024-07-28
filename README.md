# midi2osc
midi/osc to osc bridge

# Configuration
mapping.yaml
## a yaml list of {input,output} pairs
```
- input:
    channel: 8
    cc: 5
  output:
    path: /rigs/5/functionAlphaRate
- input:
    channel: 9
    note: 35
  output:
    path: /rigs/6/functionAlphaRate
```
