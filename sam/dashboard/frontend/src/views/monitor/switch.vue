<template>
  <div>
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
import { getSwitches } from '@/api/monitor'
import { STable } from '@/components'

export default {
  name: 'Switch',
  components: {
    STable
  },
  data () {
    return {
      columns: [
        { title: 'ID', dataIndex: 'id' },
        { title: '状态', dataIndex: 'active', customRender: (active) => active ? '正常' : '异常' },
        { title: '类型', dataIndex: 'type' },
        { title: '地址', dataIndex: 'lan_net' },
        { title: 'tcam使用率', dataIndex: 'tcam_usage' },
        { title: 'tcam大小', dataIndex: 'tcam_size' }
      ],
      loadData: (pagination, filters, sorter) => {
        return getSwitches().then(res => {
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
  }
}
</script>

<style scoped>

</style>
