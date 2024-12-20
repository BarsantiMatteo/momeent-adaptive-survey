//Get data file from parameters of Script tag
function getSyncScriptParams() {
    var scripts = document.getElementsByTagName('script');
    var lastScript = scripts[scripts.length-1];
    var scriptName = lastScript;

    return scriptName.getAttribute('exp_nbr');
}

// set the dimensions and margins of the graph
var margin = {top: 0, right: 30, bottom: 90, left: 60},
    width = 1000 - margin.left - margin.right,
    height = 400 - margin.top - margin.bottom;

// append the svg object to the body of the page
var svg = d3.select("#bar-chart")
            .append("svg")
            .attr("class", "svg-style")
            .append("g");

// Load data
var data = JSON.parse(window.localStorage.getItem("baseline_data"));

// Add X axis
var x = d3.scaleBand()
            .range([ 0, width ])
            .domain(data.map(function(d) { return d.Period; }))
            //.padding(0.7);
            .paddingInner(.1)
            .paddingOuter(.3)

svg.append("g")
.attr("transform", "translate(-150," + height + ")")
    .call(d3.axisBottom(x))
    .selectAll(".tick text")
    .call(wrap, 100)
    .attr("transform", "translate(45,2)")
    .attr("font-size", "16px")
    .attr("font-weight", "bold")
    .style("text-anchor", "end");

    
// Add Y axis
var y = d3.scaleLinear()
.domain([0, 4])
.range([height, 0]);

//Add "Renewable energy" rectangle
svg.selectAll("bar")
    .data(data)
    .enter()
    .append("rect")
    .attr("x", function(d) { return x(data[1].Period); })
    .attr("y", 0)
    .attr("width", 125)
    .attr("height", 310)
    .attr("fill", "#d2f8d2")
    .attr("rx", 10)
    .attr("ry", 10)
    .attr("transform", "translate(-140,0)")
    .attr("class", "renew-energy-rect")

// Baseline bars
svg.selectAll("bar")
    .data(data)
    .enter()
    .append("rect")
    .attr("x", function(d) { return x(d.Period); })
    .attr("y", function(d) {return y(d.Value); })
    .attr("width", 20)
    .attr("height", function(d) { return height - y(d.Value); })
    .attr("fill", "#D3D3D3")
    .attr("rx", 10)
    .attr("ry", 10)
    .attr("transform", "translate(-85,0)")
    .attr("class", "baseline-bar")


// initialize new bars and sliders to values of baseline barchart
var current_data = JSON.parse(window.localStorage.getItem("baseline_data"));

svg.selectAll("bar")
    .data(current_data)
    .enter()
    .append("rect")
    .attr("x", function(d) { return x(d.Period); })
    .attr("y", function(d) { return y(d.Value); })
    .attr("width", 20)
    .attr("height", function(d) { return height - y(d.Value); })
    .attr("fill", "#69b3a2")
    .attr("rx", 10)
    .attr("ry", 10)
    .attr("transform", "translate(-75,0)")
    .attr("class", "new-bar")

var morningValue   = current_data[0].Value,
    middayValue    = current_data[1].Value,
    afternoonValue = current_data[2].Value,
    eveningValue   = current_data[3].Value, 
    nightValue     = current_data[4].Value; 
    
document.getElementById("morningSlider").value = morningValue;
document.getElementById("middaySlider").value = middayValue;
document.getElementById("afternoonSlider").value = afternoonValue;
document.getElementById("eveningSlider").value = eveningValue;
document.getElementById("nightSlider").value = nightValue;

window.localStorage.setItem("current_data", JSON.stringify(current_data));

// Add legend (Manually)
var legendItemSize = 12;
var legendSpacing = 10;
var xOffset = 0;
var yOffset = 10;

var legend_data = [ { Text: "Habitual washing behavior", Color: "#D3D3D3" },
                    { Text: "New washing behavior", Color: "#69b3a2" },
                    { Text: "Renewable energy", Color: "#d2f8d2"}];

var legend = d3.select('#bar-chart-legend')
                .append('svg')
                .append('g')
                .selectAll(".legendItem")
                .data(legend_data);

legend.enter().append('rect')
        .attr('class', 'legendItem')
        .attr('width', legendItemSize)
        .attr('height', legendItemSize)
        .style('fill', d => d.Color)
        .attr('transform',
                    (d, i) => {
                        var x = xOffset;
                        var y = yOffset + (legendItemSize + legendSpacing) * i - 12;
                        return `translate(${x}, ${y})`;
                    });
                    
legend.enter().append('text')
        .attr('x', xOffset + legendItemSize + 5)
        .attr('y', (d, i) => yOffset + (legendItemSize + legendSpacing) * i)
        .text(d => d.Text); 

// A function that updates the chart when slider is moved
function updateChart(morningValue, middayValue, afternoonValue, eveningValue, nightValue) {
    //TODO optimize this
    data[0].Value = morningValue;
    data[1].Value = middayValue;
    data[2].Value = afternoonValue;
    data[3].Value = eveningValue;
    data[4].Value = nightValue;

    //Disable button if all values are 0
    if (data.every(d => d.Value == 0 ) ) {
        document.getElementById("link-to-quests").disabled = true;
        document.getElementById("stats-btn").disabled = true;
    }else {
        document.getElementById("stats-btn").disabled = false;
    }

    svg.selectAll(".new-bar").remove();
    
    svg.selectAll("bar")
        .data(data)
        .enter()
        .append("rect")
        .attr("x", function(d) { return x(d.Period); })
        .attr("y", function(d) { return y(d.Value); })
        .attr("width", 20)
        .attr("height", function(d) { return height - y(d.Value); })
        .attr("fill", "#69b3a2")
        .attr("rx", 10)
        .attr("ry", 10)
        .attr("transform", "translate(-75,0)")
        .attr("class", "new-bar")
    
    window.localStorage.setItem("current_data", JSON.stringify(data));
    return data;
}

// Listen to the sliders
//morning
d3.select("#morningSlider").on("change", function(d){
    morningValue = this.value
    current_data = updateChart(morningValue, middayValue, afternoonValue, eveningValue, nightValue)
})
//midday
d3.select("#middaySlider").on("change", function(d){
    middayValue = this.value
    current_data = updateChart(morningValue, middayValue, afternoonValue, eveningValue, nightValue)
})
//afternoon
d3.select("#afternoonSlider").on("change", function(d){
    afternoonValue = this.value
    current_data = updateChart(morningValue, middayValue, afternoonValue, eveningValue, nightValue)
})
//evening
d3.select("#eveningSlider").on("change", function(d){
    eveningValue = this.value
    current_data = updateChart(morningValue, middayValue, afternoonValue, eveningValue, nightValue)
})
//night
d3.select("#nightSlider").on("change", function(d){
    nightValue = this.value
    current_data = updateChart(morningValue, middayValue, afternoonValue, eveningValue, nightValue)
})


// Listen to the submit button
function difference(baseline_data, current_data) {
    var baseline_sum = baseline_data.reduce((partialSum, a) => partialSum + parseInt(a.Value), 0);
    var baseline_avg = baseline_sum/5 * 100;
    var current_sum = current_data.reduce((partialSum, a) => partialSum + parseInt(a.Value), 0);
    var current_avg = current_sum/5 * 100;
    return [current_sum - baseline_sum, current_avg - baseline_avg];
}


//For long x-axis labels to be written on two lines
function wrap(text, width) {
    text.each(function() {
      var text = d3.select(this),
          words = text.text().split(/\s+/).reverse(),
          word,
          line = [],
          lineNumber = 0,
          lineHeight = 1.1, // ems
          y = text.attr("y"),
          dy = parseFloat(text.attr("dy")),
          tspan = text.text(null).append("tspan").attr("x", 0).attr("y", y).attr("dy", dy + "em")
      while (word = words.pop()) {
        line.push(word)
        tspan.text(line.join(" "))
        if (tspan.node().getComputedTextLength() > width) {
          line.pop()
          tspan.text(line.join(" "))
          line = [word]
          tspan = text.append("tspan").attr("x", 0).attr("y", y).attr("dy", `${++lineNumber * lineHeight + dy}em`).text(word)
        }
      }
    })
}


d3.select("#stats-btn").on("click", function(d){    
    /* RUN DEMOD */
    function getDiff() {
        //hide stats, show loader and disable buttons
        document.getElementById("stats-icon-you").style.display = "none";    
        document.getElementById("stats-nbr-you").style.display = "none";    
        document.getElementById("stats-old-val").hidden = true; 
        document.getElementById("stats-new-val").hidden = true;
        document.getElementById("loader").style.display = "block";        
        document.getElementById("stats-btn").disabled = true;
        document.getElementById("link-to-quests").disabled = true;

        //send data to flask
        const baseline_data = JSON.parse(window.localStorage.getItem("baseline_data"))
        const current_data = JSON.parse(window.localStorage.getItem("current_data"))
        $.ajax({
            url: location.origin + "/get-res-share",
            type: 'POST',
            data: JSON.stringify({
                "data": current_data,
                "trial": "",
            }),
            contentType: "application/json",
            dataType: "json",
            success: function (response) {
                //when response is received, hide loader, re-activate buttons and show results 
                document.getElementById("stats-icon-you").style.display = "block";    
                document.getElementById("stats-nbr-you").style.display = "block";    
                document.getElementById("loader").style.display = "none"
                document.getElementById("stats-btn").disabled = false;
                document.getElementById("link-to-quests").disabled = false;

                const res_share = response.res_share;
                const diff_share = res_share - response.baseline_res_share;
            
                //update stats-you 
                document.getElementById("stats-new-val").innerHTML = "<strong>New share<br>" + res_share + " %</strong>" 
                document.getElementById("stats-old-val").hidden = false; 
                document.getElementById("stats-new-val").hidden = false;


                //update icon
                if (diff_share >= 0) {
                    document.getElementById("sub-stats-nbr-you").innerText = "+" + diff_share + " %"
                    document.getElementById("stats-icon-you").innerHTML = "<img src=\"static/img/arrow-increase-green.png\"></img>"
                } else {
                    document.getElementById("sub-stats-nbr-you").innerText = diff_share + " %"
                    document.getElementById("stats-icon-you").innerHTML = "<img src=\"static/img/arrow-decrease-red.png\"></img>"
                }            
            },
            error: function (response) {
                document.getElementById("link-to-quests").disabled = false;
                document.getElementById("loader").style.display = "none"
                alert("Error!")
            }
        });
    }
    getDiff()
})


//Send last trial's values to DB
d3.select(".link-btn").on("click", function(d){  
    $.ajax({
        url: location.origin + "/get-res-share",
        type: 'POST',
        data: JSON.stringify({
            "data": current_data,
            "trial": "FINAL",
        }),
        contentType: "application/json",
        dataType: "json",
        success: function (response) {
            window.location.assign("questions_3a");
        },
        error: function (response) {
            alert("Error!")
        }
    });
})
