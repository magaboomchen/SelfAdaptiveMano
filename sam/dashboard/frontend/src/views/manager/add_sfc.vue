<template>
  <a-form @submit="handleSubmit" :form="form">
    <a-form-item
      label="区域"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['zone', {rules:[{required: true, message: '请选择区域'}]}]">
        <a-select-option :value="'SIMULATOR_ZONE'">SIMULATOR_ZONE</a-select-option>
        <a-select-option :value="'TURBONET_ZONE'">TURBONET_ZONE</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="业务类型"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['applicationType', {rules:[{required: true, message: '请选择业务类型'}]}]">
        <a-select-option :value="'APP_TYPE_LARGE_BANDWIDTH'">高带宽</a-select-option>
        <a-select-option :value="'APP_TYPE_LOW_LATENCY'">低时延</a-select-option>
        <a-select-option :value="'APP_TYPE_HIGH_AVA'">高可用</a-select-option>
        <a-select-option :value="'APP_TYPE_LARGE_CONNECTION'">多连接</a-select-option>
        <a-select-option :value="'APP_TYPE_BEST_EFFORT'">尽力而为</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="扩缩容模式"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['scalingMode', {rules:[{required: true, message: '请选择扩缩容模式'}]}]">
        <a-select-option :value="'MANUAL_SCALE'">手动</a-select-option>
        <a-select-option :value="'AUTO_SCALE'">自动</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="路由模态"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['routingMorphic', {rules:[{required: true, message: '请选择路由模态'}]}]">
        <a-select-option :value="'IPV4_ROUTE_PROTOCOL'">IPV4</a-select-option>
        <a-select-option :value="'IPV6_ROUTE_PROTOCOL'">IPV6</a-select-option>
        <a-select-option :value="2">NDN</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="VNF设备模态"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['vnfMorphic', {rules:[{required: true, message: '请选择VNF设备模态'}]}]">
        <a-select-option :value="'AUTO'">自动</a-select-option>
        <a-select-option :value="'DEVICE_TYPE_P4'">P4</a-select-option>
        <a-select-option :value="'DEVICE_TYPE_SERVER'">x86</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="VNF"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <div class="operate">
        <a-button type="dashed" style="width: 100%" icon="plus" @click="add">添加</a-button>
      </div>
    </a-form-item>
    <a-form-item
      v-for="(k) in form.getFieldValue('vnfs')"
      :key="k"
      label=" "
      :colon="false"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol">
      <a-select v-decorator="[`vnfType[${k}]`, {rules:[{required: true, message: '请选择VNF类型'}]}]">
        <a-select-option :value="'VNF_TYPE_RATELIMITER'">速率限制器</a-select-option>
        <a-select-option :value="'VNF_TYPE_FW'">防火墙</a-select-option>
        <a-select-option :value="'VNF_TYPE_MONITOR'">Monitor</a-select-option>
      </a-select>
      <!--        <a-input></a-input>-->
    </a-form-item>
    <a-form-item
      label=" "
      :colon="false"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <div class="operate">
        <a-button type="dashed" style="width: 100%" icon="minus" @click="remove">移除</a-button>
      </div>
    </a-form-item>
    <a-form-item
      label=" "
      :colon="false"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
      style="text-align: center"
    >
      <a-button htmlType="submit" type="primary" style="width: 100%">{{ $t('form.basic-form.form.submit') }}</a-button>
    </a-form-item>
  </a-form>
</template>

<script>
import pick from 'lodash.pick'
import { addSFC } from '@/api/monitor'

const fields = ['zone', 'type', 'mode', 'routingMorphic', 'vnfMorphic']

export default {
  name: 'AddSfc',
  props: {
    record: {
      type: Object,
      default: null
    }
  },
  data () {
    return {
      labelCol: {
        xs: { span: 24 },
        sm: { span: 7 }
      },
      wrapperCol: {
        xs: { span: 24 },
        sm: { span: 13 }
      }
    }
  },
  beforeCreate () {
    this.form = this.$form.createForm(this)
    this.form.getFieldDecorator('vnfs', { initialValue: [0], preserve: true })
  },
  mounted () {
    this.record && this.form.setFieldsValue(pick(this.record, fields))
  },
  methods: {
    onOk () {
      console.log('监听了 modal ok 事件')
      return new Promise(resolve => {
        resolve(true)
      })
    },
    onCancel () {
      console.log('监听了 modal cancel 事件')
      return new Promise(resolve => {
        resolve(true)
      })
    },
    handleSubmit (e) {
      e.preventDefault()
      const { form: { validateFields } } = this
      this.visible = true
      validateFields((errors, values) => {
        if (!errors) {
          console.log('values', values)
          addSFC(values).then(res => {
            console.log(res)
            alert('请求成功')
            location.reload()
          })
        }
      })
    },
    add () {
      const { form } = this
      const vnfs = form.getFieldValue('vnfs')
      vnfs.push(vnfs.length)
      form.setFieldsValue({
        vnfs
      })
    },
    remove () {
      const { form } = this
      const vnfs = form.getFieldValue('vnfs')
      if (vnfs.length > 1) {
        vnfs.pop()
      }
      form.setFieldsValue({
        vnfs
      })
    }
  }
}
</script>
