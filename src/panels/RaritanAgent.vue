<template>
  <AgentPanelBase @clientConnected="startListening()" />

  <div class="block_holder ocs_ui">

    <!-- Left block -->
    <div class="block_unit">
      <div class="box">
        <OcsAgentHeader :panel="panel">Raritan PDU Agent</OcsAgentHeader>
        <h2>Connection</h2>
        <OpReading caption="Address" v-bind:value="pduAddress">
        </OpReading>
        <OcsLightLine caption="Status">
          <OcsLight caption="OCS" tip="Status of the connection between ocs-web and OCS crossbar."
            :value="getIndicator('ocs')" />
          <OcsLight caption="AGT" tip="Status of the connection between ocs-web and the Agent."
            :value="panel.connection_ok" />
          <OcsLight caption="ACQ" tip="Indicates that the acq appears to be acquiring data properly."
            :value="getIndicator('acq')" />
          <OcsLight caption="PDU" :tip="pduTip" :value="getIndicator('pdu')" />
        </OcsLightLine>

        <h2>Outlets</h2>

        <div v-if="panel.connection_ok">
          <span id="outlet_warning" v-if="outlet_warning"><b>{{ outlet_warning }}</b></span>
          <form class="ib_kids" v-on:submit.prevent>
            <div class="ib_row ib_header">
              <span>#</span>
              <span>name</span>
              <span class="ib_center">state</span>
              <span />
              <span class="ocs_triple ib_center">set</span>
            </div>
            <div v-for="item in outlets" :key="item.idx" class="ib_row">
              <span>{{ item.idx }}</span>
              <span :class="{
                ib_on: item.description == 'on',
                ib_off: item.description == 'off',
              }">{{ item.name }}</span>
              <span class="ib_center" :class="{
                ib_on: item.description == 'on',
                ib_off: item.description == 'off',
              }">
                <span v-if="item.locked">&#128274;</span>
                {{ item.description }}
                <span v-if="item.locked">&#128274;</span>
              </span>
              <span />
              <button :disabled="accessLevel < 1 || item.locked" @click="set_target(item.idx, 'on')">on</button>
              <button :disabled="accessLevel < 1 || item.locked" @click="set_target(item.idx, 'off')">off</button>
              <button :disabled="accessLevel < 1 || item.locked" @click="set_target(item.idx, 'cycle')">cycle</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Right block -->
    <div class="block_unit">
      <OcsProcess :op_data="ops.acq">
      </OcsProcess>

      <OcsTask :op_data="ops.set_outlet">
        <OpParam caption="Outlet (1-24)" v-model.number="ops.set_outlet.params.outlet" />
        <OpDropdown caption="State" :options="['on', 'off']" v-model="ops.set_outlet.params.state" />
      </OcsTask>

      <OcsTask :op_data="ops.cycle_outlet">
        <OpParam caption="Outlet (1-24)" v-model.number="ops.cycle_outlet.params.outlet" />
        <OpParam caption="Cycle time (s)" v-model.number="ops.cycle_outlet.params.cycle_time" />
      </OcsTask>

      <OcsTask :op_data="ops.lock_outlet">
        <OpParam caption="Outlet (1-24)" v-model.number="ops.lock_outlet.params.outlet" />
        <OpDropdown caption="Lock" :options="[true, false]" v-model="ops.lock_outlet.params.lock" />
      </OcsTask>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RaritanAgent',
  inject: ['accessLevel'],
  data: function () {
    return {
      panel: {},
      outlet_warning: null,
      outlets: {},
      ops: window.ocs_bundle.web.ops_data_init({
        'acq': {},
        'set_outlet': { params: { outlet: 1, state: 'off' } },
        'cycle_outlet': { params: { outlet: 1, cycle_time: 10 } },
        'lock_outlet': { params: { outlet: 1, lock: true } },
      }),
    }
  },
  props: {
    address: String,
  },
  computed: {
    pduAddress() {
      // Get PDU address from session data if available
      let data = this.ops.acq.session.data;
      if (data && data.address)
        return data.address;
      return this.address;
    },
    pduTip() {
      let baseTip = 'Indicates that SNMP connection to PDU is working.';
      let data = this.ops.acq.session.data;
      if (data && data.pdu_connection && data.pdu_connection.last_attempt) {
        let timeStr = window.ocs_bundle.util.get_date_time_string(
          data.pdu_connection.last_attempt, ' '
        );
        return baseTip + ' Last attempt: ' + timeStr;
      }
      return baseTip;
    },
  },
  methods: {
    update_outlet_states(_op_name, _method, _stat, _msg, session) {
      if (!this.panel.connection_ok) {
        this.outlets = {};
        this.outlet_warning = 'No connection to agent!';
        return;
      }
      if (!session.data || (session.status != 'running' && session.status != 'starting')) {
        this.outlets = {};
        this.outlet_warning = 'No outlet data -- is acq process running?';
        return;
      }

      if (window.ocs_bundle.util.timestamp_now() - session.data.timestamp > 120) {
        this.outlets = {};
        this.outlet_warning = 'Outlet data are stale -- check acq process?';
        return;
      }

      let new_info = {};
      for (let idx = 1; idx <= 24; idx++) {
        // Format: outletSwitchingState_1_01, outletSwitchingState_1_02, ... outletSwitchingState_1_24
        let k = 'outletSwitchingState_1_' + String(idx).padStart(2, '0');
        if (session.data[k]) {
          new_info[idx] = session.data[k];
          new_info[idx].idx = idx;
        }
      }
      this.outlets = new_info;
      this.outlet_warning = null;
    },
    set_target(idx, state) {
      if (state == 'cycle') {
        this.panel.client.run_task('cycle_outlet', {
          outlet: idx,
          cycle_time: 10
        });
      } else {
        this.panel.client.run_task('set_outlet', {
          outlet: idx,
          state: state
        });
      }
    },
    getIndicator(name) {
      switch (name) {
        case 'ocs':
          return window.ocs.connection.isConnected;
        case 'acq':
          {
            let session = this.ops.acq.session;
            return (session.status == 'running' ||
              session.status == 'starting');
          }
        case 'pdu':
          {
            let data = this.ops.acq.session.data;
            if (!data || !data.pdu_connection)
              return false;
            return data.pdu_connection.connected;
          }
      }
      return false;
    },
    startListening() {
      this.panel.client.add_watcher('acq', 5., this.update_outlet_states);
    },
  },
}

</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
.ib_row {
  display: grid;
  grid-template-columns: 1fr 3fr 2fr 5px 1fr 1fr 1fr;
}

.ib_row>div,
button,
span {
  font-size: 9pt;
  padding: 10px;
  margin: 2px 0px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ib_header {
  border-bottom: 1px solid black;
  padding: 10px;
}

.ib_header>span {
  font-weight: bold;
  padding: 10px 0px;
}

.ib_center {
  text-align: center;
}

.ib_on {
  background-color: #4e4;
}

.ib_off {
  background-color: #f88;
}
</style>