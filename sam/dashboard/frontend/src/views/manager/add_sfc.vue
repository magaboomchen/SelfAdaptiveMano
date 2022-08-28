<template>
  <a-form @submit="handleSubmit" :form="form">
    <a-form-item
      label="业务类型"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['type', {rules:[{required: true, message: '请选择业务类型'}]}]">
        <a-select-option :value="0">高带宽</a-select-option>
        <a-select-option :value="1">低时延</a-select-option>
        <a-select-option :value="2">高可用</a-select-option>
        <a-select-option :value="3">多连接</a-select-option>
        <a-select-option :value="4">尽力而为</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="扩缩容模式"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['mode', {rules:[{required: true, message: '请选择扩缩容模式'}]}]">
        <a-select-option :value="0">手动</a-select-option>
        <a-select-option :value="1">自动</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="路由模态"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['routingMorphic', {rules:[{required: true, message: '请选择路由模态'}]}]">
        <a-select-option :value="0">IPV4</a-select-option>
        <a-select-option :value="1">IPV6</a-select-option>
        <a-select-option :value="2">NDN</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="VNF设备模态"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <a-select v-decorator="['vnfMorphic', {rules:[{required: true, message: '请选择VNF设备模态'}]}]">
        <a-select-option :value="0">自动</a-select-option>
        <a-select-option :value="1">P4</a-select-option>
        <a-select-option :value="2">x86</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item
      label="VNF"
      :labelCol="labelCol"
      :wrapperCol="wrapperCol"
    >
      <div class="operate">
        <a-button type="dashed" style="width: 100%" icon="plus" @click="vnfs.push(1)">添加</a-button>
      </div>
      <div v-for="(vnf,index) in vnfs" :key="index">
        <a-select :vnf="vnf">
          <a-select-option :value="0">速率限制器</a-select-option>
          <a-select-option :value="1">防火墙</a-select-option>
          <a-select-option :value="2">Monitor</a-select-option>
        </a-select>
        <!--        <a-input></a-input>-->
      </div>
      <div class="operate">
        <a-button type="dashed" style="width: 100%" icon="minus" @click="vnfs.length>1?vnfs.pop():null">移除</a-button>
      </div>
    </a-form-item>
  </a-form>
</template>

<script>
import pick from 'lodash.pick'

const fields = ['type', 'mode', 'routingMorphic', 'vnfMorphic', 'vnfs']

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
      },
      form: this.$form.createForm(this),
      vnfs: [1]
    }
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
    handleSubmit () {
      const { form: { validateFields } } = this
      this.visible = true
      validateFields((errors, values) => {
        if (!errors) {
          console.log('values', values)
        }
      })
    }
  }
}
</script>
