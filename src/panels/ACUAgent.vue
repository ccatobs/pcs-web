<template>
  <AgentPanelBase />

  <div class="block_holder ocs_ui">

    <!-- Left block -->
    <div class="block_unit">
      <div class="box">
        <OcsAgentHeader :panel="panel">ACU Agent (PCS)</OcsAgentHeader>

        <h2>Connection</h2>
        <OpReading caption="Address" v-bind:value="address">
        </OpReading>

        <OcsLightLine caption="OCS/Agent">
          <OcsLight caption="OCS" tip="Status of the connection between ocs-web and OCS crossbar."
            :value="getIndicator('ocs')" />
          <OcsLight caption="AGT" tip="Status of the connection between ocs-web and the Agent."
            :value="getIndicator('agent')" />
          <OcsLight caption="BCAST" type="multi" tip="Will show green/good when 'broadcast' process appears to be
                     running and acquiring data normally." :value="getIndicator('broadcast')" />
        </OcsLightLine>

        <!-- Current Position from broadcast data -->
        <h2>Position (from Broadcast)</h2>
        <OpReading caption="Azimuth" :stale="broadcastIsStale" v-bind:value="currentPosition('Azimuth')">
        </OpReading>
        <OpReading caption="Elevation" :stale="broadcastIsStale" v-bind:value="currentPosition('Elevation')">
        </OpReading>
        <OpReading caption="Az Velocity" :stale="broadcastIsStale" v-bind:value="currentPosition('Azimuth_Velocity')">
        </OpReading>
        <OpReading caption="El Velocity" :stale="broadcastIsStale" v-bind:value="currentPosition('Elevation_Velocity')">
        </OpReading>
        <OpReading caption="Timestamp" :stale="broadcastIsStale" v-bind:value="broadcastTimestamp">
        </OpReading>

        <h2>Activity</h2>
        <OpReading caption="Status" v-bind:value="currentMotion">
        </OpReading>
      </div>
    </div>

    <!-- Right block -->
    <div class="block_unit">

      <!-- go_to task -->
      <OcsTask :show_abort="true" :op_data="ops.go_to">
        <OpParam caption="Az (deg)" v-model.number="ops.go_to.params.az" />
        <OpParam caption="El (deg)" v-model.number="ops.go_to.params.el" />
      </OcsTask>

      <!-- az_scan task - uses custom start button because params must be wrapped in scan_params dict -->
      <OcsTask :show_start="false" :show_abort="true" :op_data="ops.az_scan">
        <OpParam caption="Start Time" placeholder="2025-01-28T12:00:00Z" v-model="scan_form.start_time" />
        <OpParam caption="Turnaround (s)" v-model.number="scan_form.turnaround_time" />
        <OpParam caption="Elevation (deg)" v-model.number="scan_form.elevation" />
        <OpParam caption="Speed (deg/s)" v-model.number="scan_form.speed" />
        <OpParam caption="Num Scans" v-model.number="scan_form.num_scans" />
        <OpParam caption="Az Min (deg)" v-model.number="scan_form.az_min" />
        <OpParam caption="Az Max (deg)" v-model.number="scan_form.az_max" />
        <div class="ocs_row">
          <label></label>
          <button :disabled="accessLevel < 1" @click="start_az_scan()">Start az_scan</button>
        </div>
      </OcsTask>

      <!-- fromfile_scan task -->
      <OcsTask :show_abort="true" :op_data="ops.fromfile_scan">
        <OpParam caption="Scan Filename" v-model="ops.fromfile_scan.params.scan_filename" />
      </OcsTask>

      <!-- broadcast process -->
      <OcsProcess :op_data="ops.broadcast">
        <OpParam caption="Auto Enable" v-model="ops.broadcast.params.auto_enable" />
      </OcsProcess>

      <!-- Autofill for any operations not explicitly shown -->
      <OcsOpAutofill :ops_parent="ops" />

    </div>
  </div>
</template>

<script>
export default {
  name: 'ACUAgent',
  props: {
    address: String,
  },
  inject: ['accessLevel'],
  data: function () {
    return {
      panel: {},
      // Form data for az_scan - separate from ops because we need to build the nested dict
      // The agent expects: {scan_params: {start_time, turnaround_time, elevation, speed, num_scans, azimuth_range}}
      scan_form: {
        start_time: '',
        turnaround_time: 5.0,
        elevation: 45.0,
        speed: 1.0,
        num_scans: 10,
        az_min: 150.0,
        az_max: 210.0,
      },
      ops: window.ocs_bundle.web.ops_data_init({
        // Tasks
        go_to: {
          params: {
            az: 180,
            el: 60,
          },
        },
        az_scan: {
          params: {
            scan_params: {},  // Will be populated by start_az_scan()
          },
        },
        fromfile_scan: {
          params: {
            scan_filename: '',
          },
        },
        // Processes
        broadcast: {
          params: {
            auto_enable: true,
          },
        },
        execute_scan: {
          params: {},
        },
      }),
    }
  },
  methods: {
    // az_scan requires params wrapped in a scan_params dict
    start_az_scan() {
      const scan_params = {
        start_time: this.scan_form.start_time,
        turnaround_time: parseFloat(this.scan_form.turnaround_time),
        elevation: parseFloat(this.scan_form.elevation),
        speed: parseFloat(this.scan_form.speed),
        num_scans: parseInt(this.scan_form.num_scans),
        azimuth_range: [
          parseFloat(this.scan_form.az_min),
          parseFloat(this.scan_form.az_max)
        ]
      };

      window.ocs_bundle.ui_run_task(this.address, 'az_scan',
        { scan_params: scan_params });
    },

    // Get current position from broadcast session.data
    currentPosition(key) {
      let data = this.ops.broadcast.session.data;
      if (!data || data[key] === undefined)
        return '?';
      let val = Number(data[key]);
      if (isNaN(val))
        return '?';
      return val.toFixed(4);
    },

    getIndicator(name) {
      let brd_stale_time = 5;

      let ocs_ok = window.ocs.connection.isConnected;
      if (name == 'ocs')
        return ocs_ok;

      if (name == 'agent')
        return this.panel.connection_ok;

      if (!ocs_ok || !this.panel.connection_ok)
        return 'notapplic';

      // For the UDP broadcast process
      if (name == 'broadcast') {
        let brd = this.ops.broadcast.session;
        if (brd.status != 'running')
          return false;
        // PCS broadcast uses 'Time' field
        let brd_time = brd.data['Time'];
        if (!brd_time || (
          window.ocs_bundle.util.timestamp_now() - brd_time > brd_stale_time))
          return 'warning';
        return true;
      }

      return 'notapplic';
    },
  },
  computed: {
    broadcastIsStale() {
      return this.getIndicator('broadcast') !== true;
    },

    broadcastTimestamp() {
      let data = this.ops.broadcast.session.data;
      if (!data || !data['Time'])
        return '?';
      return window.ocs_bundle.util.get_date_time_string(data['Time'], ' ');
    },

    currentMotion() {
      // Figure out a string to describe what we're doing now
      let activities = {
        "Az Scanning": this.ops.az_scan.session,
        "Moving": this.ops.go_to.session,
        "File Scanning": this.ops.fromfile_scan.session,
        "Executing Scan": this.ops.execute_scan.session,
      };
      let texts = [];
      for (const [k, v] of Object.entries(activities)) {
        if (v && v.status && v.status != 'unknown' && v.status != 'done')
          texts.push(k);
      }
      if (!texts.length)
        return '(idle)';
      return texts.join(' AND ');
    },
  },
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped></style>