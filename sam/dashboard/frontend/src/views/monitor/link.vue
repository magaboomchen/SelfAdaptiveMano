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
import { getLinks } from '@/api/monitor'
import { STable } from '@/components'

export default {
  name: 'Link',
  components: {
    STable
  },
  data () {
    return {
      columns: [
        { title: '源交换机', dataIndex: 'src' },
        { title: '目的交换机', dataIndex: 'dst' },
        { title: '状态', dataIndex: 'active', customRender: (active) => active ? '正常' : '异常' },
        { title: '使用率', dataIndex: 'util', customRender: util => (util * 100).toFixed(2) + '%' },
        { title: '带宽', dataIndex: 'bandwidth', customRender: bw => bw + 'Gbps' }
      ],
      loadData: (pagination, filters, sorter) => {
        return getLinks().then(res => {
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
