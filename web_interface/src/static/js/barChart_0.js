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


// initialize variables of sliders
var morningValue = 0, middayValue = 0, afternoonValue = 0, eveningValue = 0, nightValue = 0;
var data = [{ Period: "morning 06:00-09:59", Value: "0" },
            { Period: "midday 10:00-13:59", Value: "0" },
            { Period: "afternoon 14:00-17:59", Value: "0" },
            { Period: "evening 18:00-21:59", Value: "0" },
            { Period: "night 22:00-05:59", Value: "0" }];

// Add X axis
var x = d3.scaleBand()
            .range([ 0, width ])
            .domain(data.map(function(d) { return d.Period; }))
            .paddingInner(.1)
            .paddingOuter(.3)

svg.append("g")
    .attr("transform", "translate(145," + height + ")")
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


// Bars
// A function that updates the chart when slider is moved
function updateChart(morningValue, middayValue, afternoonValue, eveningValue, nightValue) {
    data[0].Value = morningValue;
    data[1].Value = middayValue;
    data[2].Value = afternoonValue;
    data[3].Value = eveningValue;
    data[4].Value = nightValue;

    //Disable button if all values are 0
    if (data.every(d => d.Value == 0 ) ) {
        document.getElementById("link-to-quests").disabled = true;
    }else {
        document.getElementById("link-to-quests").disabled = false;
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
        .attr("transform", "translate(210,0)")
        .attr("class", "new-bar")

    window.localStorage.setItem("baseline_data", JSON.stringify(data));
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

//For long x-axis labels to be written on two lines
function wrap(text, width) {
    text.each(function() {
      var text = d3.select(this),
          words = text.text().split(/\s+/).reverse(),
          word,
          line = [],
          lineNumber = 0,
          lineHeight = 1.5, // ems
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
          tspan = text.append("tspan")
                      .attr("x", 0)
                      .attr("y", y)
                      .attr("dy", `${++lineNumber * lineHeight + dy}em`)
                      .text(word)
        }
      }
    })
}

//Send the baseline values to Flask
d3.select(".link-btn").on("click", function(d){  
    $.ajax({
        url: location.origin + "/get-baseline-values",
        type: 'POST',
        data: JSON.stringify({
            "data": data
        }),
        contentType: "application/json",
        dataType: "json",
        success: function (response) {
            window.location.assign("questions_0");
        },
        error: function (response) {
            alert("Error!")
        }
    });
})
