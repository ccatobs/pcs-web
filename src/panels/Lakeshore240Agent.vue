<template>
  <AgentPanelBase />

  <div class="block_holder ocs_ui">

    <!-- Left block -->
    <div class="block_unit">
      <div class="box">
        <OcsAgentHeader :panel="panel">Lakeshore240Agent</OcsAgentHeader>
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
        <div class="ocs_triple data_table box">
          <div class="data_row header data_column ">
            <span>Channel</span><span>T</span><span>V</span><span>age</span>
          </div>
          <div class="data_row"
               v-for="chan in computedChannels"
               v-bind:key="chan[0]">
            <span v-for="d in chan" v-html="d" v-bind:key="d" />
          </div>
        </div>
      </div>
    </div>

    <!-- Right block -->
    <div class="block_unit">

      <OcsTask
        :op_data="ops.init_lakeshore">
      </OcsTask>

      <OcsProcess
        :op_data="ops.acq"
      />

      <div class="box cal_section">
        <h3>Calibration Curve Operations</h3>

        <div v-if="isAcqRunning" class="warning_text">
          Stop the acq process before modifying calibration curves.
        </div>

        <OcsTask :show_start="false" :op_data="ops.get_curve_header">
          <OpParam
            caption="Channel (1-8)"
            v-model.number="ops.get_curve_header.params.channel" />
          <div class="ocs_row">
            <label></label>
            <button :disabled="accessLevel < 1 || isAcqRunning" @click="startGetCurveHeader()">Start</button>
          </div>
        </OcsTask>

        <div v-if="hasCurveHeaderData" class="curve_header_results">
          <OpReading
            caption="Sensor Model"
            :value="curveHeader.Sensor_Model" />
          <OpReading
            caption="Serial Number"
            :value="curveHeader.Serial_Number" />
          <OpReading
            caption="Data Format"
            :value="curveHeader.Data_Format" />
          <OpReading
            caption="SetPoint Limit"
            :value="curveHeader.SetPoint_Limit" />
          <OpReading
            caption="Temp Coefficient"
            :value="curveHeader.Temperature_Coefficient" />
          <OpReading
            caption="Breakpoints"
            :value="curveHeader.Number_of_Breakpoints" />
          <div class="queried_channel">
            Channel {{ lastQueriedChannel }}
          </div>
        </div>

        <OcsTask :show_start="false" :op_data="ops.upload_cal_curve">
          <OpParam
            caption="Channel (1-8)"
            v-model.number="ops.upload_cal_curve.params.channel" />
          <OpParam
            caption="File Path"
            v-model="ops.upload_cal_curve.params.filename" />
          <div class="ocs_row">
            <label></label>
            <button :disabled="accessLevel < 1 || isAcqRunning" @click="startUploadCalCurve()">Start</button>
          </div>
        </OcsTask>
        <div class="help_text">File path is on the agent host system.</div>
      </div>

      <div class="box cal_section">
        <h3>Channel Configuration</h3>

        <div v-if="isAcqRunning" class="warning_text">
          Stop the acq process before modifying channel values.
        </div>

        <OcsTask :show_start="false" :op_data="ops.get_values">
          <OpParam
            caption="Channel (1-8)"
            v-model.number="ops.get_values.params.channel" />
          <div class="ocs_row">
            <label></label>
            <button :disabled="accessLevel < 1 || isAcqRunning"
                    @click="startGetValues()">Start</button>
          </div>
          <div v-for="item in Object.entries(ops.get_values.session.data)"
               v-bind:key="item[0]">
            <OpReading
              v-if="item[0] !== 'last_update'"
              :caption="item[0]"
              :value="item[1]" />
          </div>
        </OcsTask>

        <OcsTask :show_start="false" :op_data="ops.set_values">
          <OpParam
            caption="Channel (1-8)"
            v-model.number="ops.set_values.params.channel" />
          <OpParam
            caption="Sensor (1=Diode, 2=Plat, 3=NTC)"
            modelType="blank_to_null"
            v-model.number="ops.set_values.params.sensor" />
          <OpParam
            caption="Auto Range (0=Off, 1=On)"
            modelType="blank_to_null"
            v-model.number="ops.set_values.params.auto_range" />
          <OpParam
            caption="Range (0-8, NTC only)"
            modelType="blank_to_null"
            v-model.number="ops.set_values.params.range" />
          <OpParam
            caption="Current Reversal (0=Off, 1=On)"
            modelType="blank_to_null"
            v-model.number="ops.set_values.params.current_reversal" />
          <OpParam
            caption="Units (1=K, 2=C, 3=Sensor, 4=F)"
            modelType="blank_to_null"
            v-model.number="ops.set_values.params.units" />
          <OpParam
            caption="Enabled (0=Off, 1=On)"
            modelType="blank_to_null"
            v-model.number="ops.set_values.params.enabled" />
          <OpParam
            caption="Name"
            modelType="blank_to_null"
            v-model="ops.set_values.params.name" />
          <div class="ocs_row">
            <label></label>
            <button :disabled="accessLevel < 1 || isAcqRunning"
                    @click="startSetValues()">Start</button>
          </div>
        </OcsTask>
      </div>

      <OcsOpAutofill
        :ops_parent="ops"
      />

    </div>

  </div>
</template>

<script>
  export default {
    name: 'Lakeshore240Agent',
    props: {
      address: String,
    },
    inject: ['accessLevel'],
    data: function () {
      return {
        panel: {},
        extension: 5,
        precision: 3,
        lastQueriedChannel: null,
        ops: window.ocs_bundle.web.ops_data_init({
          init_lakeshore: {},
          acq: {},
          get_curve_header: {
            params: { channel: 1 },
          },
          upload_cal_curve: {
            params: { channel: 1, filename: '' },
          },
          get_values: {
            params: { channel: 1 },
          },
          set_values: {
            params: {
              channel: 1,
              sensor: null,
              auto_range: null,
              range: null,
              current_reversal: null,
              units: null,
              enabled: null,
              name: null,
            },
          },
        }),
      }
    },
    methods: {
      startGetCurveHeader() {
        window.ocs_bundle.ui_run_task(this.address, 'get_curve_header',
                                      this.ops.get_curve_header.params);
      },
      startUploadCalCurve() {
        window.ocs_bundle.ui_run_task(this.address, 'upload_cal_curve',
                                      this.ops.upload_cal_curve.params);
      },
      startGetValues() {
        window.ocs_bundle.ui_run_task(this.address, 'get_values',
                                      this.ops.get_values.params);
      },
      startSetValues() {
        window.ocs_bundle.ui_run_task(this.address, 'set_values',
                                      this.ops.set_values.params);
      },
    },
    computed: {
      computedChannels() {
        // Set this.channel_data to any recent measurements.
        let stale = 500;
        let new_data = [];
        let now = window.ocs_bundle.util.timestamp_now();
        let fields = this.ops.acq.session.data.fields;
        let dt = now - this.ops.acq.session.data.timestamp;
        if (fields) {
          Object.keys(fields).forEach((name) => {
            if (dt < stale) {
              let T = window.ocs_bundle.util.pad_decimal(
                fields[name].T.toFixed(this.precision), this.extension);
              let R = window.ocs_bundle.util.pad_decimal(
                fields[name].V.toFixed(this.precision), this.extension);
              let oldness = window.ocs_bundle.util.pad_decimal(
                window.ocs_bundle.util.human_timespan(dt), 4);
              new_data.push([name, T, R, oldness]);
            }
          });
        }
        return new_data;
      },
      isAcqRunning() {
        let status = this.ops.acq.session.status;
        return status == 'running' || status == 'starting';
      },
      curveHeader() {
        return this.ops.get_curve_header.session.data || {};
      },
      hasCurveHeaderData() {
        return Object.keys(this.curveHeader).length > 0;
      },
    },
    watch: {
      'ops.get_curve_header.session.status'(newVal) {
        if (newVal == 'done') {
          this.lastQueriedChannel = this.ops.get_curve_header.params.channel;
        }
      },
    },
  }
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
  .header > span {
    font-weight: bold;
  }
  .data_row > span {
    text-align: center;
  }
  .data_table > div {
    display: grid;
    grid-template-columns: 35% 2fr 2fr 2fr;
    grid-gap: 5px;
  }
  .data_table > div:nth-child(odd) {
    background-color: #f8f;
  }
  .data_table > div:nth-child(even) {
    background-color: #fdf;
  }
  .data_table > div:first-child {
    background-color: #fff;
  }
  .cal_section {
    margin-top: 10px;
  }
  .warning_text {
    color: #c00;
    font-weight: bold;
    padding: 5px 0;
  }
  .help_text {
    font-size: 9pt;
    color: #666;
    padding: 2px 10px;
  }
  .curve_header_results {
    background-color: #f8f;
    padding: 5px;
    margin: 5px 0;
  }
  .queried_channel {
    font-size: 9pt;
    color: #666;
    text-align: right;
  }
</style>
