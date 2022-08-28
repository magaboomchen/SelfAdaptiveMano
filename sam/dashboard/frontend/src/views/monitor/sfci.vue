<template>
  <div>
    <div class="operate">
      <a-button type="dashed" style="width: 100%" icon="plus" @click="add">添加</a-button>
    </div>
    <div style="height: 30px;"></div>
    <s-table
      ref="table"
      size="default"
      rowKey="key"
      :columns="columns"
      :data="loadData"
      showPagination="auto"
    >

    </s-table>
  </div>
</template>

<script>
import { getSFCIs } from '@/api/monitor'
import { STable } from '@/components'
import TaskForm from '@/views/list/modules/TaskForm'

export default {
  name: 'SFCI',
  components: {
    TaskForm,
    STable
  },
  data () {
    return {
      columns: [
        { title: 'ID', dataIndex: 'id' },
        { title: 'vnfi序列长度', dataIndex: ['sfci', 'vnfiSequenceLength'] },
        { title: '转发路径', dataIndex: ['sfci', 'forwardingPath'], customRender: list => JSON.stringify(list) },
        { title: '路由模态', dataIndex: 'routingMorphic' }
      ],
      loadData: (pagination, filters, sorter) => {
        return getSFCIs().then(res => {
          const start = (pagination.pageNo - 1) * pagination.pageSize
          const end = start + pagination.pageSize
          return {
            'data': res.slice(start, end),
            'pageSize': pagination.pageSize,
            'pageNo': pagination.pageNo,
            'totalPage': Math.ceil(res.length / pagination.pageSize),
            'totalCount': res.length
          }
        })
      }

    }
  },
  methods: {
    add () {
      this.$dialog(TaskForm,
        // component props
        {
          record: {},
          on: {
            ok () {
              console.log('ok 回调')
            },
            cancel () {
              console.log('cancel 回调')
            },
            close () {
              console.log('modal close 回调')
            }
          }
        },
        // modal props
        {
          title: '新增',
          width: 700,
          centered: true,
          maskClosable: false
        })
    }
  },
  created () {
    this.intervalId = setInterval(() => {
      this.$refs.table.refresh(false, false)
    }, 2000)
  },
  destroyed () {
    clearInterval(this.intervalId)
  }
}
</script>

<style scoped>

</style>
