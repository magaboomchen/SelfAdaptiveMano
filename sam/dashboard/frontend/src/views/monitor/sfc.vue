<template>
  <div>
    <!--    <div class='operate'>-->
    <!--      <a-button type='dashed' style='width: 100%' icon='plus' @click='add'>添加</a-button>-->
    <!--    </div>-->
    <!--    <div style='height: 30px;'></div>-->
    <s-table
      ref="table"
      size="default"
      rowKey="key"
      :columns="columns"
      :data="loadData"
      showPagination="auto"
    >
      <span slot="action" slot-scope="text, record">
        <template>
          <a @click="handleDelete(record)">删除</a>
        </template>
      </span>
    </s-table>
  </div>
</template>

<script>
import { getSFCs, delSFC } from '@/api/monitor'
import { STable } from '@/components'

export default {
  name: 'Sfc',
  components: {
    STable
  },
  data () {
    return {
      columns: [
        { title: 'UUID', dataIndex: 'uuid' },
        { title: '状态', dataIndex: 'state' },
        { title: 'zone', dataIndex: 'zone' },
        { title: '业务类型', dataIndex: ['sfc', 'applicationType'] },
        { title: '扩缩容模式', dataIndex: ['sfc', 'scalingMode'] },
        { title: '路由模态', dataIndex: ['sfc', 'routingMorphic'] },
        { title: 'sfci数量', dataIndex: ['sfcis'], customRender: (sfcis) => sfcis.length },
        { title: '操作', dataIndex: ['action'], scopedSlots: { customRender: 'action' }, width: '80px' }
      ],
      loadData: (pagination, filters, sorter) => {
        return getSFCs().then(res => {
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
  created () {
    this.intervalId = setInterval(() => {
      this.$refs.table.refresh(false, false)
    }, 2000)
  },
  destroyed () {
    clearInterval(this.intervalId)
  },
  methods: {
    handleDelete (e) {
      delSFC(e.uuid).then(() => {
        this.$refs.table.refresh(false, false)
      })
    }
  }
}
</script>

<style scoped>

</style>
