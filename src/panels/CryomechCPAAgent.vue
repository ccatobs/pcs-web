<!--

CryomechCPAAgent

This component is activated when a specialized panel does not exist
for a particular agent class.  It displays the agent address and
connection status, and then provides generic (parameter-free) controls
for all tasks and processes detected in the agent.

This code can be used as a template / starting point for implementing
specialized agent panels.

-->
<template>
  <AgentPanelBase />

  <div class="block_holder ocs_ui">

    <!-- Left block -->
    <div class="block_unit">
      <div class="box">
        <OcsAgentHeader>Cryomech CPA Agent</OcsAgentHeader>
        <h2>Connection</h2>
        <OpReading
          caption="Address"
          v-bind:value="address">
        </OpReading>
        <OpReading
          caption="Connection"
          mode="ok"
          v-bind:value="panel.connection_ok">
        </OpReading>
        <h2>Status</h2>
        <div v-for="chan in statusData"
             v-bind:key="chan[0]">
          <OpReading
            :caption="chan[0]"
            v-bind:value="chan[1]" />
        </div>
      </div>
    </div>

    <!-- Right block -->
    <div class="block_unit">

      <OcsTask
        :op_data="ops.init">
      </OcsTask>

      <OcsProcess
        :op_data="ops.acq"
      />

      <OcsTask
        :show_start="false"
        op_name="power_ptc"
        :op_data="ops.power_ptc">
        <div class="ocs_row">
          <label>Set State</label>
          <button
            :disabled="accessLevel < 1"
            @click="set_ptc_state(true)">On</button>
          <button
            :disabled="accessLevel < 1"
            @click="set_ptc_state(false)">Off</button>
        </div>
      </OcsTask>
    </div>

  </div>
</template>

<script>
  export default {
    name: 'CryomechCPAAgent',
    props: {
      address: String,
    },
    inject: ['accessLevel'],
    data: function () {
      return {
        panel: {},
        groups: {
          status: {
            name: "Status",
            fields: [
              {key: "Compressor_State", label: "Compressor State"},
              {key: "Coolant_In", label: "Coolant In"},
              {key: "Coolant_Out", label: "Coolant Out"},
              {key: "Oil_Temp", label: "Oil Temp"},
              {key: "Helium_Temp", label: "Helium Temp"},
              {key: "Low_Pressure", label: "Low Pressure"},
              {key: "High_Pressure", label: "High Pressure"},
              {key: "Delta_Pressure_Average", label: "Delta Pressure Avg"},
              {key: "Motor_Current", label: "Motor Current"},
              {key: "Hours_of_Operation", label: "Hours of Operation"},
            ]
          },
        },
        ops: window.ocs_bundle.web.ops_data_init({
          acq: {},
        }),
      }
    },
    computed: {
      statusData() {
        let new_data = [];
        let field_data = this.ops.acq.session.data;
        if (field_data) {
          this.groups.status.fields.forEach(function(field) {
            let label = field.label ? field.label : field.key;
            let data = field_data[field.key];
            let raw_data = data ? data.description : "?";
            new_data.push([label, raw_data]);
          });
        }
        return new_data;
      },
    },
    methods: {
      set_ptc_state(state) {
        let task = {true: 'on', false: 'off'}[state];
        this.ops.power_ptc.params['state'] = task;
        window.ocs_bundle.ui_run_task(this.address, 'power_ptc',
                                      this.ops.power_ptc.params);
      },
    }
  }
</script>