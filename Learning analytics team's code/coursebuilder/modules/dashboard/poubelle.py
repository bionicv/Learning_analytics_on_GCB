     ## Chart showing the percentage of success per assessment

            """

                $(function () {
    $('#container1').highcharts({
        chart: {
            type: 'column'
        },
        title: {
            text: 'Percentage of success per assessement'
        },
        subtitle: {
            text: 'Source: Datastore'
        },
        xAxis: {
        
            categories: [
                'Pre-course assessment',
                'Mid-course assessment',
                'Final-course assessment',
                ]
        },
        yAxis: {
            min: 0,
            title: {
                text: 'Number of students '
            }
        },
        tooltip: {
            headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
            pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
                '<td style="padding:0"><b>{point.y:.1f} students</b></td></tr>',
            footerFormat: '</table>',
            shared: true,
            useHTML: true
        },
        plotOptions: {
            column: {
                pointPadding: 0.2,
                borderWidth: 0
            }
        },
        series: [{
            name: 'Students enrolled',
            data: [ %d, %d, %d ],"""  %(int(total_student), int(total_student), int(total_student) )


                details +="""
                
            color: '#08298A'

        }"""

            # All the different cases need to be taken into account after    
                if (Num_questions_Pre>0 and Num_questions_Mid > 0 and Num_questions_Fin >0):
                    details += """,
        {
            name: 'Students having done the assessment',

                data: [ %d, %d, %d ],  color: 'blue'

        },""" %(int(stats['scores']['Pre'][0]), int(stats['scores']['Mid'][0]), int(stats['scores']['Fin'][0]) )


                    details +="""
               {
                name: 'Students having got < 50',
                data: [%d, %d, %d],""" %(int(stats['scores']['Pre'][0])- int(Num_student_having_succeed[0]), int(stats['scores']['Mid'][0])-int(Num_student_having_succeed[1]), int(stats['scores']['Fin'][0])-int(Num_student_having_succeed[2]))

                    details +="""

                color: '#FF0000'

            }, {
                name: 'Student having got > 50',
                data: [ %d, %d, %d], """ %(int(Num_student_having_succeed[0]), int(Num_student_having_succeed[1]), int(Num_student_having_succeed[2]))

                    details +="""

                color: '#FFFF00'

            }, {
                name: 'Student having got >= 75',
                data: [%d,%d, %d],""" %(int(dict_bests[0]), int(dict_bests[1]), int(dict_bests[2]))

                    details += """
                color: '#298A08'

            }"""

                details += """
        ]
    });
});
                """

